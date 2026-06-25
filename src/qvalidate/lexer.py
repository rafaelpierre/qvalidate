"""Multi-mode q lexer.

Hand-written port of server/src/parser/lexer.ts (a Chevrotain multi-mode lexer).
Behaviour preserved:

  * **First-match-wins** -- at each offset the patterns for the active mode are
    tried in order; the first that matches is taken (not longest-match).
  * **longer_alt** -- if the chosen token defines a ``longer_alt`` (keywords ->
    Identifier) and that alternative matches a strictly longer span at the same
    offset, the alternative is emitted instead. Stops ``selectfoo`` lexing as
    ``select`` + ``foo``.
  * **mode stack** -- ``push_mode`` / ``pop_mode`` tokens switch lexing modes
    (strings, comments, test blocks).

Unlike Chevrotain's ``safeMode``, characters that match nothing in ``q_mode``
are *not* silently dropped: they are recorded as :class:`LexError` so the
validation layer can report them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .grammar import DEFAULT_MODE, MODES, TokenType


class Token:
    """A lexed token plus the slots the semantic pass later fills in.

    Position fields mirror Chevrotain / the TS ``Token`` interface and are
    1-based: ``start_column`` / ``end_column`` are the columns of the first and
    *last* characters of the token's image.
    """

    __slots__ = (
        "image",
        "token_type",
        "start_offset",
        "end_offset",
        "start_line",
        "start_column",
        "end_line",
        "end_column",
        # semantic-pass annotations (see source.py)
        "index",
        "namespace",
        "scope",
        "mode",
        "feat",
        "rank",
        "call",
        "error",
    )

    def __init__(
        self,
        image: str,
        token_type: TokenType,
        start_offset: int,
        end_offset: int,
        start_line: int,
        start_column: int,
        end_line: int,
        end_column: int,
    ) -> None:
        self.image = image
        self.token_type = token_type
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column
        self.index: Optional[int] = None
        self.namespace: Optional[str] = None
        self.scope: Optional["Token"] = None
        self.mode: Optional["Token"] = None
        self.feat: Optional["Token"] = None
        self.rank: Optional[int] = None
        self.call: Optional["Token"] = None
        self.error: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Token({self.token_type.name}, {self.image!r}, {self.start_line}:{self.start_column})"


@dataclass
class LexError:
    """A character that no token pattern in the active mode could consume."""

    offset: int
    line: int
    column: int
    char: str


@dataclass
class LexResult:
    tokens: List[Token] = field(default_factory=list)
    errors: List[LexError] = field(default_factory=list)
    #: True if a string mode was still open at end of input.
    unterminated_string: bool = False


def _consume(image: str, line: int, col: int):
    """Return (end_line, end_col, next_line, next_col) after consuming *image*.

    ``end_*`` are the 1-based position of the image's last character;
    ``next_*`` are the position of the following character.
    """
    end_line, end_col = line, col
    for ch in image:
        end_line, end_col = line, col
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1
    return end_line, end_col, line, col


def tokenize(text: str) -> LexResult:
    result = LexResult()
    pos = 0
    line = 1
    col = 1
    n = len(text)
    mode_stack: List[str] = [DEFAULT_MODE]

    while pos < n:
        mode = mode_stack[-1]
        chosen_type: Optional[TokenType] = None
        match = None

        for tt in MODES[mode]:
            m = tt.regex.match(text, pos)
            if m is not None and m.end() > pos:
                chosen_type = tt
                match = m
                break

        if chosen_type is None or match is None:
            # No token matched: record a lex error and skip one character so we
            # keep scanning (and can report every offending position).
            ch = text[pos]
            result.errors.append(LexError(pos, line, col, ch))
            _, _, line, col = _consume(ch, line, col)
            pos += 1
            continue

        # longer_alt: prefer the alternative if it matches a strictly longer span.
        if chosen_type.longer_alt is not None:
            alt = chosen_type.longer_alt.regex.match(text, pos)
            if alt is not None and alt.end() > match.end():
                chosen_type = chosen_type.longer_alt
                match = alt

        image = match.group()
        end_line, end_col, next_line, next_col = _consume(image, line, col)

        token = Token(
            image=image,
            token_type=chosen_type,
            start_offset=pos,
            end_offset=match.end(),
            start_line=line,
            start_column=col,
            end_line=end_line,
            end_column=end_col,
        )
        result.tokens.append(token)

        if chosen_type.pop_mode and len(mode_stack) > 1:
            mode_stack.pop()
        if chosen_type.push_mode:
            mode_stack.append(chosen_type.push_mode)

        pos = match.end()
        line, col = next_line, next_col

    result.unterminated_string = "string_mode" in mode_stack
    return result
