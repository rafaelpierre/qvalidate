"""Validation verdict + metadata tests, driven by the corpus directories."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from qvalidate import validate  # noqa: E402

CORPUS = Path(__file__).parent / "corpus"


def _cases(folder):
    d = CORPUS / folder
    return sorted(d.glob("*.q"))


@pytest.mark.parametrize("path", _cases("valid"), ids=lambda p: p.stem)
def test_valid_corpus(path):
    result = validate(path.read_text())
    assert result.valid, [
        (d.code, d.line, d.column, d.message) for d in result.diagnostics
    ]


# Map each invalid fixture to the diagnostic code it must surface.
_EXPECTED = {
    "unbalanced_paren": "UNBALANCED_PAREN",
    "unbalanced_brace": "UNBALANCED_BRACE",
    "unbalanced_bracket": "UNBALANCED_BRACKET",
    "stray_close": "UNEXPECTED_CLOSE",
    "mismatched": "MISMATCHED_DELIMITER",
    "unterminated_string": "UNCLOSED_STRING",
    "invalid_escape": "INVALID_ESCAPE",
    "select_no_from": "QSQL_MISSING_FROM",
}


@pytest.mark.parametrize("path", _cases("invalid"), ids=lambda p: p.stem)
def test_invalid_corpus(path):
    result = validate(path.read_text())
    assert not result.valid
    expected = _EXPECTED[path.stem]
    codes = [d.code for d in result.diagnostics]
    assert expected in codes, codes


# --- metadata spot-checks --------------------------------------------------


def test_metadata_select():
    r = validate("select px, sz from trades where sym=`AAPL")
    assert r.valid
    assert r.metadata.sql[0].op == "select"
    assert r.metadata.sql[0].table == "trades"
    assert set(r.metadata.sql[0].columns) >= {"px", "sz", "sym"}


def test_metadata_definitions_and_references():
    r = validate("f:{[a;b] a+b}; g:f")
    assert r.valid
    assert "f" in r.metadata.defined_symbols
    assert "g" in r.metadata.defined_symbols
    assert "f" in r.metadata.references


def test_metadata_namespace():
    r = validate("\\d .foo\nx:1")
    assert ".foo" in r.metadata.namespaces
    assert ".foo.x" in r.metadata.defined_symbols


def test_result_is_typed_and_serialisable():
    from qvalidate import Diagnostic, QueryMetadata, SqlBlock, ValidationResult

    r = validate("select a from t")

    # Typed pydantic models, not loose dicts.
    assert isinstance(r, ValidationResult)
    assert isinstance(r.metadata, QueryMetadata)
    assert all(isinstance(d, Diagnostic) for d in r.diagnostics)
    assert all(isinstance(b, SqlBlock) for b in r.metadata.sql)

    # First-class serialisation, no dataclasses.asdict glue.
    assert isinstance(r.model_dump(), dict)
    assert r.model_dump_json()  # JSON string, must not raise

    # Round-trips back into a fully-typed model.
    assert ValidationResult.model_validate_json(r.model_dump_json()) == r
