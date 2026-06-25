"""Semantic analysis: scope, assignment and namespace resolution.

Faithful port of server/src/parser/source.ts (the ``Source`` class plus its
``Name`` / ``Scope`` / ``Type`` / ``Param`` / ``Callable`` helpers). A single
left-to-right pass over the lexed tokens annotates each token with its enclosing
scope, parenthesis/bracket mode, namespace and expression index, and collects
``definitions`` (assignments) and ``references`` (uses).

Two intentional deviations from the TS original, both called out in the plan:

  * Reference resolution (``_process``) is indexed by name into a dict, so it is
    O(n) rather than the original's O(n^2) ``find`` loops.
  * The ``Colon`` reference-removal path checks membership before removing,
    avoiding a JavaScript ``splice(indexOf(x), 1)`` quirk that deletes the last
    element when ``x`` is absent.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .grammar import (
    Colon,
    Command,
    Comparator,
    Cond,
    CutDrop,
    DoubleColon,
    EndOfLine,
    ExitCommentBegin,
    Identifier,
    Iterator,
    LBracket,
    LCurly,
    LParen,
    LSql,
    Operator,
    RBracket,
    RCurly,
    RParen,
    RSql,
    SemiColon,
    WhiteSpace,
)
from .lexer import LexResult, Token, tokenize

_STACK_CLEARERS = (Iterator, DoubleColon, Comparator, CutDrop, Operator, Cond)
_COMMAND_NS = re.compile(r"^\\d[ \t]+", re.DOTALL)


def Peek(tokens: List[Token]) -> Optional[Token]:
    return tokens[-1] if tokens else None


def Type(token: Optional[Token]):
    return token.token_type if token else None


def Scope(token: Optional[Token]) -> Optional[Token]:
    return token.scope if token else None


def Name(token: Optional[Token]) -> str:
    if not token:
        return ""
    if token.namespace == "." or token.image.startswith("."):
        return token.image
    return f"{token.namespace}.{token.image}"


def Param(token: Optional[Token]) -> bool:
    return Type(token.feat) is LCurly if token else False


def Callable(token: Optional[Token]) -> bool:
    return bool(token and token.call)


def Namespace(token: Token) -> str:
    name = Name(token)
    if name.startswith("."):
        parts = name.split(".", 2)
        if len(parts) > 1:
            return parts[1]
    return ""


def _seek(tokens: List[Token], index: int, step: int = 1) -> Optional[Token]:
    index += step
    while 0 <= index < len(tokens) and tokens[index].token_type in (
        WhiteSpace,
        EndOfLine,
    ):
        index += step
    return tokens[index] if 0 <= index < len(tokens) else None


class Source:
    def __init__(self, uri: str, text: str) -> None:
        self.uri = uri
        self.lex: LexResult = tokenize(text)
        self.tokens: List[Token] = self.lex.tokens
        self.errors: List[Token] = []
        self.references: List[Token] = []
        self.definitions: List[Token] = []

    @classmethod
    def create(cls, uri: str, text: str) -> "Source":
        source = cls(uri, text)
        source._parse()
        source._process()
        return source

    @property
    def symbols(self) -> List[Token]:
        return [t for t in self.definitions if t.scope is None]

    def token_at(self, line: int, character: int) -> Optional[Token]:
        """Find the token covering a 0-based (line, character) position."""
        for token in self.tokens:
            sl = (token.start_line or 1) - 1
            sc = (token.start_column or 1) - 1
            el = (token.end_line or 1) - 1
            ec = token.end_column or 1
            if sl <= line and el >= line and sc <= character and ec >= character:
                return token
        return None

    # -- internals ---------------------------------------------------------

    def _handle_rcurly(self, scope_tok: Token) -> None:
        defs = [t for t in self.definitions if t.scope is scope_tok]
        rank = scope_tok.rank or 0
        for reference in self.references:
            if reference.scope is not scope_tok:
                continue
            if reference.image.startswith("."):
                reference.scope = None
            else:
                name = Name(reference)
                found = any(name == Name(t) for t in defs)
                if not found:
                    if rank == 0 and name in ("x", "y", "z"):
                        continue
                    reference.scope = None

    def _parse(self) -> None:
        modes: List[Token] = []
        feats: List[Token] = []
        scope: List[Token] = []
        stack: List[Token] = []

        index = 0
        namespace = "."

        def assign(pattern: bool = True) -> int:
            count = 0
            while stack:
                tok = stack.pop()
                if tok.token_type is Identifier:
                    self.definitions.append(tok)
                    count += 1
                    if not pattern:
                        stack.clear()
                        break
            return count

        for i, current in enumerate(self.tokens):
            current.mode = Peek(modes)
            current.feat = Peek(feats)
            current.scope = Peek(scope)
            current.index = index
            current.namespace = namespace

            t = current.token_type

            if t is LParen:
                modes.append(current)
                stack.append(current)
            elif t is RParen:
                if Type(current.feat) is LParen:
                    feats.pop()
                if modes:
                    modes.pop()
                stack.append(current)
            elif t is LCurly:
                scope.append(current)
                modes.append(current)
                stack.clear()
                prev = Peek(self.definitions)
                if prev:
                    prev.call = current
                self.definitions.append(current)
            elif t is RCurly:
                top = Peek(scope)
                if top and Type(top) is LCurly:
                    self._handle_rcurly(top)
                if scope:
                    scope.pop()
                if modes:
                    modes.pop()
                stack.clear()
            elif t is LBracket:
                prev = _seek(self.tokens, i, -1)
                if prev and Type(prev) in (LCurly, LParen):
                    feats.append(prev)
                modes.append(current)
                stack.clear()
            elif t is RBracket:
                feat = current.feat
                if feat is not None and feat.token_type is LCurly:
                    feat.rank = assign()
                    feats.pop()
                elif Type(current.feat) is not LParen:
                    stack.clear()
                if modes:
                    modes.pop()
            elif t is LSql:
                modes.append(current)
                stack.clear()
            elif t is RSql:
                if modes:
                    modes.pop()
                stack.clear()
            elif t is Identifier:
                stack.append(current)
                self.references.append(current)
            elif t is Colon:
                if Type(current.feat) is LParen or Type(current.mode) is LSql:
                    for tok in stack:
                        if tok in self.references:
                            self.references.remove(tok)
                    stack.clear()
                elif Type(current.feat) is not LCurly:
                    first = stack[0] if stack else None
                    assign(Type(Peek(stack)) is RParen and Type(first) is LParen)
            elif t is SemiColon:
                if (
                    Type(current.feat) is not LCurly
                    and Type(current.feat) is not LParen
                    and Type(current.mode) is not LParen
                ):
                    stack.clear()
                if not current.mode:
                    index += 1
            elif t is EndOfLine:
                nxt = self.tokens[i + 1] if i + 1 < len(self.tokens) else None
                if Type(nxt) is not WhiteSpace:
                    stack.clear()
                    index += 1
            elif t is Command:
                parts = _COMMAND_NS.split(current.image)
                if len(parts) > 1:
                    namespace = parts[1] or "."
                stack.clear()
            elif t in _STACK_CLEARERS:
                stack.clear()
            elif t is ExitCommentBegin:
                return

    def _process(self) -> None:
        first_by_name: dict = {}
        for token in self.definitions:
            name = Name(token)
            if name not in first_by_name:
                first_by_name[name] = token
        for reference in self.references:
            definition = first_by_name.get(Name(reference))
            if definition is not None and definition.call:
                reference.call = definition.call
