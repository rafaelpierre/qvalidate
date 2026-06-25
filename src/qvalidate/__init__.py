"""qvalidate -- validate generated kdb/q queries for agent tools.

A high-level agent generates a full kdb/q query; hand the complete string to
:func:`validate` and get back a pass/fail verdict, parse-time error diagnostics,
and structured query metadata the agent can use to self-correct.

    >>> from qvalidate import validate
    >>> r = validate("select px, sz from trades where sym=`AAPL")
    >>> r.valid
    True
    >>> r.metadata.sql[0].table
    'trades'

Lower-level building blocks (:func:`tokenize`, :class:`Source`) are exported for
advanced use.
"""

from __future__ import annotations

from .diagnostics import (
    Diagnostic,
    QueryMetadata,
    Severity,
    SqlBlock,
    ValidationResult,
)
from .lexer import LexError, LexResult, Token, tokenize
from .source import Source
from .validate import validate

__all__ = [
    "validate",
    "ValidationResult",
    "Diagnostic",
    "QueryMetadata",
    "SqlBlock",
    "Severity",
    "Source",
    "tokenize",
    "Token",
    "LexResult",
    "LexError",
]

__version__ = "0.1.0"
