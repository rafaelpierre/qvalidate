"""Structured query metadata derived from a :class:`~qvalidate.source.Source`.

This is descriptive only -- it never contributes to the pass/fail verdict. It
gives the agent context to reason about and self-correct a query: what it
defines, what it references, which namespaces it touches, and the qSQL
tables/columns it reads.
"""

from __future__ import annotations

from typing import List, Optional

from .diagnostics import QueryMetadata, SqlBlock
from .grammar import (
    Identifier,
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
)
from .lexer import Token
from .source import Name, Source

_OPENERS = (LParen, LBracket, LCurly)
_CLOSERS = (RParen, RBracket, RCurly)


def _dedup(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _extract_sql(tokens: List[Token]) -> List[SqlBlock]:
    blocks: List[SqlBlock] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.token_type is not LSql:
            i += 1
            continue

        op = tok.image
        depth = 0
        seen_from = False
        table: Optional[str] = None
        table_token: Optional[Token] = None
        columns: List[str] = []

        j = i + 1
        while j < n:
            tj = tokens[j]
            tt = tj.token_type
            if depth == 0 and tt in (SemiColon, EndOfLine):
                # End of the qSQL statement (whitespace continuation aside).
                if tt is EndOfLine:
                    nxt = tokens[j + 1] if j + 1 < n else None
                    if nxt is not None and nxt.token_type is WhiteSpace:
                        j += 1
                        continue
                break
            if tt is LSql:  # a new query begins
                break
            if tt in _OPENERS:
                depth += 1
            elif tt in _CLOSERS:
                if depth == 0:
                    break
                depth -= 1
            elif tt is RSql and depth == 0:
                seen_from = True
            elif tt is Identifier:
                if seen_from and table is None:
                    table = tj.image
                    table_token = tj
                else:
                    columns.append(tj.image)
            j += 1

        cols = _dedup([c for c in columns if not (table_token and c == table)])
        blocks.append(SqlBlock(op=op, table=table, columns=cols))
        i = j
    return blocks


def build_metadata(source: Source) -> QueryMetadata:
    defined = _dedup(
        [Name(t) for t in source.definitions if t.token_type is Identifier]
    )
    references = _dedup([Name(t) for t in source.references])
    # The namespace value already carries its leading dot (e.g. ".foo"); "." is
    # the default (global) namespace and is not reported.
    namespaces = _dedup(
        [t.namespace for t in source.tokens if t.namespace and t.namespace != "."]
    )
    sql = _extract_sql(source.tokens)
    return QueryMetadata(
        defined_symbols=defined,
        references=references,
        namespaces=namespaces,
        sql=sql,
    )
