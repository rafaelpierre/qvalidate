"""Result types returned by :func:`qvalidate.validate`.

All dataclasses are plain and JSON-serialisable via ``dataclasses.asdict`` so an
agent layer can hand a result straight to an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class Severity(IntEnum):
    ERROR = 1
    WARNING = 2


@dataclass
class Diagnostic:
    code: str
    message: str
    #: 1-based position of the first offending character.
    line: int
    column: int
    #: 1-based position of the last offending character.
    end_line: int
    end_column: int
    severity: int = int(Severity.ERROR)


@dataclass
class SqlBlock:
    op: str  # select | exec | update | delete
    table: Optional[str]
    columns: List[str] = field(default_factory=list)


@dataclass
class QueryMetadata:
    defined_symbols: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    namespaces: List[str] = field(default_factory=list)
    sql: List[SqlBlock] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    diagnostics: List[Diagnostic] = field(default_factory=list)
    metadata: QueryMetadata = field(default_factory=QueryMetadata)
