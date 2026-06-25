"""Semantic-analysis tests, including the TS parser cases that concern parsing.

Ported from test/suite/server/parser.test.ts (the "should not throw" cases).
The stylistic-lint cases from that file are intentionally dropped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from qvalidate import Source  # noqa: E402
from qvalidate.source import Name  # noqa: E402


@pytest.mark.parametrize("text", ["", " ", "\n"])
def test_does_not_throw_on_empty(text):
    Source.create("u", text)


@pytest.mark.parametrize(
    "text",
    ["}", "{\n}", "]", "[\n]", ")", "(\n)", "from", "select\nfrom"],
)
def test_does_not_throw_on_missing_scope(text):
    Source.create("u", text)


def test_global_assignment_is_a_symbol():
    src = Source.create("u", "a:1")
    names = [Name(t) for t in src.symbols]
    assert "a" in names


def test_lambda_local_is_scoped_not_global():
    src = Source.create("u", "{a:1; a}")
    # "a" is local to the lambda, so it is not a top-level symbol.
    assert "a" not in [Name(t) for t in src.symbols]


def test_namespace_qualifies_names():
    src = Source.create("u", "\\d .foo\nx:1")
    assert ".foo.x" in [Name(t) for t in src.definitions]


def test_function_definition_links_call():
    src = Source.create("u", "f:{x+1}")
    f = next(t for t in src.definitions if t.image == "f")
    assert f.call is not None  # f is callable (assigned a lambda)
