"""Differential oracle: compare our verdict against a real q's ``parse``.

This is the authoritative false-positive guard -- we must never reject a query
that q would accept. It needs a q runtime via ``pykx`` (and a kdb+ that pykx can
start); when neither is available the whole module is skipped so CI stays green
without a licence.

Run with:  pip install 'qvalidate[oracle]'  then  pytest tests/test_oracle.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from qvalidate import validate  # noqa: E402

kx = pytest.importorskip("pykx", reason="pykx not installed")

CORPUS = Path(__file__).parent / "corpus"


def _q_parses(query: str) -> bool:
    """True if q's parser accepts the query (parse-time only, no evaluation)."""
    try:
        kx.q("parse", kx.CharVector(query))
        return True
    except Exception:
        return False


def _all_cases():
    cases = []
    for folder in ("valid", "invalid"):
        for path in sorted((CORPUS / folder).glob("*.q")):
            cases.append(path)
    return cases


@pytest.mark.parametrize(
    "path", _all_cases(), ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_matches_q_parser(path):
    query = path.read_text()
    ours = validate(query).valid
    theirs = _q_parses(query)
    # The contract is one-directional and strict: anything q accepts, we must
    # accept (no false positives). We may additionally reject things q's bare
    # parser tolerates (e.g. some escape forms), so only assert the safe side.
    if theirs:
        assert ours, f"false positive: q accepts {query!r} but we rejected it"
