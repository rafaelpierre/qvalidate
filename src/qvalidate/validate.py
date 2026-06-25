"""The validation verdict layer.

The ported lexer/parser are deliberately lenient, so this module adds the
explicit "would ``q`` reject this at parse time?" checks. It flags *only*
failures, never style:

  * unbalanced / mismatched / stray ``( ) [ ] { }``
  * unterminated string literals
  * invalid string escape sequences
  * characters that cannot be lexed at all
  * a ``select`` / ``exec`` qSQL template with no ``from``

It never flags unknown identifiers, unknown tables/columns, or anything
stylistic -- those depend on session/schema state we do not have, and a false
positive would block the agent.
"""

from __future__ import annotations

from typing import List, Optional

from .diagnostics import (
    Diagnostic,
    QueryMetadata,
    Severity,
    ValidationResult,
)
from .grammar import (
    LBracket,
    LCurly,
    LParen,
    LSql,
    RBracket,
    RCurly,
    RParen,
    RSql,
    SemiColon,
    EndOfLine,
    WhiteSpace,
    StringBegin,
    StringEscape,
)
from .lexer import Token
from .metadata import build_metadata
from .source import Source

_OPEN_FOR = {LParen: RParen, LBracket: RBracket, LCurly: RCurly}
_CLOSE_FOR = {RParen: LParen, RBracket: LBracket, RCurly: LCurly}
_KIND_NAME = {
    LParen: "PAREN",
    LBracket: "BRACKET",
    LCurly: "BRACE",
    RParen: "PAREN",
    RBracket: "BRACKET",
    RCurly: "BRACE",
}
_VALID_ESCAPE_CHARS = {"n", "r", "t", "\\", "/", '"'}


def _diag(code: str, message: str, token: Token, severity: int = int(Severity.ERROR)):
    return Diagnostic(
        code=code,
        message=message,
        line=token.start_line,
        column=token.start_column,
        end_line=token.end_line,
        end_column=token.end_column,
        severity=severity,
    )


def _check_delimiters(tokens: List[Token]) -> List[Diagnostic]:
    """Balanced-delimiter pass. String/comment contents are already excluded
    from the token stream, so a left-to-right stack walk is exact."""
    diagnostics: List[Diagnostic] = []
    stack: List[Token] = []
    for token in tokens:
        tt = token.token_type
        if tt in _OPEN_FOR:
            stack.append(token)
        elif tt in _CLOSE_FOR:
            if not stack:
                diagnostics.append(
                    _diag(
                        "UNEXPECTED_CLOSE",
                        f"Unexpected closing '{token.image}' with no matching opener.",
                        token,
                    )
                )
                continue
            opener = stack.pop()
            if _CLOSE_FOR[tt] is not opener.token_type:
                diagnostics.append(
                    _diag(
                        "MISMATCHED_DELIMITER",
                        f"Closing '{token.image}' does not match opening "
                        f"'{opener.image}'.",
                        token,
                    )
                )
    for opener in stack:
        kind = _KIND_NAME[opener.token_type]
        diagnostics.append(
            _diag(
                f"UNBALANCED_{kind}",
                f"Unclosed '{opener.image}'.",
                opener,
            )
        )
    return diagnostics


def _invalid_escape(image: str) -> bool:
    """Port of checks.ts:checkEscape. ``image`` is e.g. ``\\n`` or ``\\378``."""
    rest = image[1:]
    if rest in _VALID_ESCAPE_CHARS:
        return False
    try:
        value = int(rest)
    except ValueError:
        value = 0
    return (not value) or value < 100 or value > 377


def _check_escapes(tokens: List[Token]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    for token in tokens:
        if token.token_type is StringEscape and _invalid_escape(token.image):
            diagnostics.append(
                _diag(
                    "INVALID_ESCAPE",
                    f"Invalid string escape sequence '{token.image}'. Valid "
                    r"escapes are \n \r \t \\ \/ \" and octal \100-\377.",
                    token,
                )
            )
    return diagnostics


def _check_unterminated_string(source: Source) -> List[Diagnostic]:
    if not source.lex.unterminated_string:
        return []
    opener: Optional[Token] = None
    for token in source.tokens:
        if token.token_type is StringBegin:
            opener = token
    if opener is None:
        return []
    return [
        _diag(
            "UNCLOSED_STRING",
            'Unterminated string literal (missing closing ").',
            opener,
        )
    ]


def _check_lex_errors(source: Source) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    for err in source.lex.errors:
        diagnostics.append(
            Diagnostic(
                code="LEX_ERROR",
                message=f"Unexpected character {err.char!r}.",
                line=err.line,
                column=err.column,
                end_line=err.line,
                end_column=err.column,
                severity=int(Severity.ERROR),
            )
        )
    return diagnostics


def _check_qsql(tokens: List[Token]) -> List[Diagnostic]:
    """Conservative: a ``select`` / ``exec`` statement with no ``from``."""
    diagnostics: List[Diagnostic] = []
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if tok.token_type is not LSql:
            continue
        if tok.image.lower() not in ("select", "exec"):
            continue
        depth = 0
        seen_from = False
        j = i + 1
        while j < n:
            tj = tokens[j]
            tt = tj.token_type
            if depth == 0 and tt in (SemiColon, EndOfLine):
                if tt is EndOfLine:
                    nxt = tokens[j + 1] if j + 1 < n else None
                    if nxt is not None and nxt.token_type is WhiteSpace:
                        j += 1
                        continue
                break
            if tt is LSql:
                break
            if tt in (LParen, LBracket, LCurly):
                depth += 1
            elif tt in (RParen, RBracket, RCurly):
                if depth == 0:
                    break
                depth -= 1
            elif tt is RSql and depth == 0:
                seen_from = True
                break
            j += 1
        if not seen_from:
            diagnostics.append(
                _diag(
                    "QSQL_MISSING_FROM",
                    f"qSQL '{tok.image}' statement is missing a 'from' clause.",
                    tok,
                )
            )
    return diagnostics


def validate(query: str, *, uri: str = "<query>") -> ValidationResult:
    """Validate a full kdb/q query string.

    Returns a :class:`ValidationResult` with a pass/fail ``valid`` flag, a list
    of parse-time ``diagnostics``, and descriptive ``metadata`` (defined symbols,
    references, namespaces, qSQL tables/columns).
    """
    source = Source.create(uri, query)

    diagnostics: List[Diagnostic] = []
    diagnostics += _check_lex_errors(source)
    diagnostics += _check_unterminated_string(source)
    diagnostics += _check_delimiters(source.tokens)
    diagnostics += _check_escapes(source.tokens)
    diagnostics += _check_qsql(source.tokens)

    diagnostics.sort(key=lambda d: (d.line, d.column))

    metadata: QueryMetadata = build_metadata(source)
    valid = not any(d.severity == int(Severity.ERROR) for d in diagnostics)
    return ValidationResult(valid=valid, diagnostics=diagnostics, metadata=metadata)
