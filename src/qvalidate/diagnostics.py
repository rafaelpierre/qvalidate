"""Typed result models returned by :func:`qvalidate.validate`.

All result types are `pydantic <https://docs.pydantic.dev>`_ models, so an agent
layer gets validated, fully-typed objects with first-class serialisation built
in -- ``result.model_dump()`` for a dict, ``result.model_dump_json()`` for a
JSON string -- no ``dataclasses.asdict`` glue required.
"""

from __future__ import annotations

from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Severity(IntEnum):
    ERROR = 1
    WARNING = 2


class Diagnostic(BaseModel):
    """A single parse-time problem, with a 1-based source span."""

    model_config = ConfigDict(use_enum_values=True)

    code: str
    message: str
    #: 1-based position of the first offending character.
    line: int
    column: int
    #: 1-based position of the last offending character.
    end_line: int
    end_column: int
    severity: Severity = Severity.ERROR


class SqlBlock(BaseModel):
    """A qSQL statement reduced to its operation, table and columns."""

    op: str  # select | exec | update | delete
    table: Optional[str] = None
    columns: List[str] = Field(default_factory=list)


class QueryMetadata(BaseModel):
    """Descriptive context an agent can reason over -- never a verdict input."""

    defined_symbols: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    namespaces: List[str] = Field(default_factory=list)
    sql: List[SqlBlock] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """The top-level verdict: ``valid`` plus diagnostics and metadata."""

    valid: bool
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    metadata: QueryMetadata = Field(default_factory=QueryMetadata)
