"""Lexer-level tests: token kinds, ordering, longer_alt, modes, lex errors."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qvalidate import tokenize  # noqa: E402
from qvalidate.grammar import (  # noqa: E402
    Identifier,
    LSql,
    NumberLiteral,
)


def kinds(text):
    return [(t.token_type.name, t.image) for t in tokenize(text).tokens]


def test_empty_and_whitespace():
    assert tokenize("").tokens == []
    assert [k for k, _ in kinds(" ")] == ["WhiteSpace"]
    assert [k for k, _ in kinds("\n")] == ["EndOfLine"]


def test_keyword_vs_identifier_longer_alt():
    # "select" is a qSQL keyword...
    toks = tokenize("select").tokens
    assert toks[0].token_type is LSql
    # ...but "selectfoo" must lex as a single Identifier, not select + foo.
    toks = tokenize("selectfoo").tokens
    assert len(toks) == 1
    assert toks[0].token_type is Identifier
    assert toks[0].image == "selectfoo"


def test_symbol_and_number_literals():
    assert ("SymbolLiteral", "`AAPL") in kinds("`AAPL")
    toks = tokenize("42").tokens
    assert toks[0].token_type is NumberLiteral


def test_string_mode_round_trip():
    text = '"abc"'
    ks = [k for k, _ in kinds(text)]
    assert ks[0] == "StringBegin"
    assert ks[-1] == "StringEnd"
    assert tokenize(text).unterminated_string is False


def test_unterminated_string_flagged():
    res = tokenize('"abc')
    assert res.unterminated_string is True


def test_unlexable_char_is_lex_error():
    # A bare control char that matches nothing in q_mode.
    res = tokenize("\x00")
    assert len(res.errors) == 1
    assert res.errors[0].char == "\x00"


def test_positions_are_one_based():
    tok = tokenize("ab").tokens[0]
    assert (tok.start_line, tok.start_column) == (1, 1)
    assert (tok.end_line, tok.end_column) == (1, 2)  # last char of "ab"
