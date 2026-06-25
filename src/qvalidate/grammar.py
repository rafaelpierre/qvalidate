"""Token definitions and per-mode ordering for the q lexer.

Ported from the kx-vscode language server:
  server/src/parser/tokens.ts, literals.ts, keywords.ts, ranges.ts

The patterns are lifted near-verbatim. Two JavaScript-isms are mapped:
  - the ``/i`` flag becomes ``re.IGNORECASE``
  - ``(?<!.)`` (start-of-line) and ``(?<=[ \\t])`` lookbehind/lookahead survive
    Python's ``re.match(text, pos)`` because ``pos`` keeps full-string context.

Chevrotain picks the *first* token in mode order whose pattern matches at the
current offset (first-match-wins, not longest-match), so the order of the lists
at the bottom of this module is semantically load-bearing.
"""

from __future__ import annotations

import re
from typing import List, Optional


class TokenType:
    """A lexer token kind: a compiled anchored pattern plus mode metadata."""

    __slots__ = (
        "name",
        "regex",
        "push_mode",
        "pop_mode",
        "longer_alt",
    )

    def __init__(
        self,
        name: str,
        pattern: str,
        *,
        flags: int = 0,
        push_mode: Optional[str] = None,
        pop_mode: bool = False,
        longer_alt: Optional["TokenType"] = None,
    ) -> None:
        self.name = name
        self.regex = re.compile(pattern, flags)
        self.push_mode = push_mode
        self.pop_mode = pop_mode
        self.longer_alt = longer_alt

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"TokenType({self.name})"


# --- ranges.ts: mode-switching tokens -------------------------------------

CommentBegin = TokenType(
    "CommentBegin", r"(?<!.)/[ \t]*(?!.)", push_mode="comment_mode"
)
CommentEnd = TokenType("CommentEnd", r"(?<!.)\\[ \t]*(?!.)", pop_mode=True)
ExitCommentBegin = TokenType(
    "ExitCommentBegin", r"(?<!.)\\[ \t]*(?!.)", push_mode="exit_comment_mode"
)
StringBegin = TokenType("StringBegin", r'"', push_mode="string_mode")
StringEnd = TokenType("StringEnd", r'"', pop_mode=True)
TestBegin = TokenType(
    "TestBegin",
    r"(?<!.)[ \t]*(x?feature)\b(.*)",
    flags=re.IGNORECASE,
    push_mode="test_mode",
)


# --- tokens.ts: comments, docs, operators, delimiters ---------------------

TestBlock = TokenType(
    "TestBlock",
    r"(?<!.)[ \t]*(x?(?:replicate|timelimit|tolerance|feature|should|bench))\b(.*)",
    flags=re.IGNORECASE,
)
TestLambdaBlock = TokenType(
    "TestLambdaBlock",
    r"(?<!.)[ \t]*(x?(?:before each|after each|behaviour|baseline|teardown"
    r"|property|to match|skip if|expect|before|after|setup))\b(.*)",
    flags=re.IGNORECASE,
)
Documentation = TokenType(
    "Documentation",
    r"(?:(?<=[ \t])|(?<!.))/{1,2}[ \t]*(@(?:default-subcategory|default-category"
    r"|file[oO]verview|subcategory|deprecated|overview|category|doctest|example"
    r"|private|typedef|returns?|throws|author|param|kind|name|todo|desc|see|end))\b.*",
)
LineComment = TokenType("LineComment", r"(?:(?<=[ \t])|(?<!.))/.*")
Command = TokenType(
    "Command", r"(?<!.)\\(?:cd|ts|[abBcCdefglopPrsStTuvwWxz12_\\])(?:(?! /).)*"
)
WhiteSpace = TokenType("WhiteSpace", r"[ \t]+")
EndOfLine = TokenType("EndOfLine", r"(?:\r?\n)+")
CommentEndOfLine = TokenType("CommentEndOfLine", r"(?:\r?\n)+")
StringEscape = TokenType("StringEscape", r"\\([0-9]{3}|.{1})")
Iterator = TokenType("Iterator", r"[\\'/]:")
DoubleColon = TokenType("DoubleColon", r"::")
Comparator = TokenType("Comparator", r"(?:<=|>=|<>|[><=~])")
CutDrop = TokenType("CutDrop", r"(?<![a-zA-Z])_")
Dict = TokenType("Dict", r"!")
Operator = TokenType("Operator", r"[\\.,'|^?#@&%*+-]")
Cond = TokenType("Cond", r"\$")
Colon = TokenType("Colon", r":")
SemiColon = TokenType("SemiColon", r";")
LParen = TokenType("LParen", r"\(")
RParen = TokenType("RParen", r"\)")
LBracket = TokenType("LBracket", r"\[")
RBracket = TokenType("RBracket", r"]")
LCurly = TokenType("LCurly", r"{")
RCurly = TokenType("RCurly", r"}")


# --- literals.ts ----------------------------------------------------------

SymbolLiteral = TokenType("SymbolLiteral", r"`[/.:\w]*")
DateTimeLiteral = TokenType(
    "DateTimeLiteral", r"\d{4}\.\d{2}\.\d{2}T(?:\d{2}:){1,2}\d{2}\.?\d*"
)
TimeStampLiteral = TokenType(
    "TimeStampLiteral", r"\d{4}\.\d{2}\.\d{2}D(?:\d{2}:){1,2}\d{2}\.?\d*"
)
DateLiteral = TokenType("DateLiteral", r"\d{4}\.\d{2}\.\d{2}")
MonthLiteral = TokenType("MonthLiteral", r"\d{4}\.\d{2}m")
TimeLiteral = TokenType("TimeLiteral", r"(?:0D)?(?:\d{2}:){1,2}\d{2}\.?\d*")
InfinityLiteral = TokenType("InfinityLiteral", r"(?:0N[deghjmnptuvz]?|-?0[wW]|0n)")
BinaryLiteral = TokenType("BinaryLiteral", r"[01]+b")
ByteLiteral = TokenType("ByteLiteral", r"0x(?:[0-9a-fA-F]{2})+")
NumberLiteral = TokenType(
    "NumberLiteral", r"-?(?:\d+\.\d+|\.\d+|\d+\.|\d+)(?:e[+-]?\d?\d)?[jhife]?"
)
CharLiteral = TokenType("CharLiteral", r"\S")
CommentLiteral = TokenType("CommentLiteral", r"\S")


# --- keywords.ts (identifiers, keywords, reserved) ------------------------

Identifier = TokenType("Identifier", r"\.?[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)*")
System = TokenType("System", r"system", longer_alt=Identifier)
Control = TokenType("Control", r"(?:while|if|do)", longer_alt=Identifier)
LSql = TokenType("LSql", r"(?:select|exec|update|delete)", longer_alt=Identifier)
RSql = TokenType("RSql", r"from", longer_alt=Identifier)
Keyword = TokenType(
    "Keyword",
    r"(?:reciprocal|distinct|ceiling|reverse|sublist|ungroup|delete|deltas|differ"
    r"|enlist|except|getenv|hclose|hcount|insert|mcount|ratios|rotate|select|setenv"
    r"|signum|string|system|tables|update|upsert|within|xgroup|count|cross|dsave"
    r"|fills|first|fkeys|floor|group|gtime|hopen|idesc|inter|lower|ltime|ltrim|parse"
    r"|peach|prior|read0|read1|reval|rload|rsave|rtrim|union|upper|value|views|where"
    r"|while|xcols|xdesc|xprev|xrank|acos|ajf0|asin|asof|atan|attr|avgs|binr|cols"
    r"|desc|each|eval|exec|exit|flip|from|hdel|hsym|iasc|keys|last|like|load|mavg"
    r"|maxs|mdev|meta|mins|mmax|mmin|msum|next|null|over|prds|prev|rand|rank|raze"
    r"|save|scan|scov|sdev|show|sqrt|sums|svar|trim|type|view|wavg|wsum|xasc|xbar"
    r"|xcol|xexp|xkey|xlog|abs|aj0|ajf|all|and|any|asc|avg|bin|cor|cos|cov|csv|cut"
    r"|dev|div|ema|exp|fby|get|ijf|inv|key|ljf|log|lsq|max|md5|med|min|mmu|mod|neg"
    r"|not|prd|set|sin|ssr|sum|tan|til|ujf|var|wj1|aj|do|ej|if|ij|in|lj|or|pj|ss|sv"
    r"|uj|vs|wj)",
    longer_alt=Identifier,
)
Reserved = TokenType(
    "Reserved",
    r"(?:\.h\.(?:iso8601|code|edsn|fram|HOME|htac|html|http|logo|text|hta|htc|hug"
    r"|nbr|pre|val|xmp|br|c0|c1|cd|ed|ha|hb|hc|he|hn|hp|hr|ht|hu|hy|jx|sa|sb|sc|td"
    r"|tx|ty|uh|xd|xs|xt|d)|\.j\.(?:jd|[jk])|\.m\.(?:addmonths|dpfts|dsftg|addr|btoa"
    r"|dpft|hdpf|host|view|chk|def|ens|fmt|fpn|fps|fsn|ind|j10|j12|MAP|opt|par|res"
    r"|sbt|trp|x10|x12|b6|bt|bv|Cf|cn|dd|en|ff|fk|fs|ft|fu|gc|gz|hg|hp|id|nA|pd|PD"
    r"|pf|pn|pt|pv|PV|qp|qt|s1|ts|ty|vp|Xf|[aADfklMPsuvVwx])|\.[Qq]\.(?:addmonths"
    r"|dpfts|dsftg|addr|btoa|dpft|hdpf|host|sha1|view|chk|def|ens|fmt|fpn|fps|fsn"
    r"|ind|j10|j12|MAP|opt|par|res|sbt|trp|x10|x12|b6|bt|bv|Cf|cn|dd|en|fc|ff|fk|fs"
    r"|ft|fu|gc|gz|hg|hp|id|nA|pd|PD|pf|pn|pt|pv|PV|qp|qt|s1|ts|ty|vp|Xf"
    r"|[aADfklMPsSuvVwx])|\.z\.(?:exit|ac|bm|ex|ey|pc|pd|pg|ph|pi|pm|po|pp|pq|ps|pw"
    r"|ts|vs|wc|wo|ws|zd|[abcdDefhikKlnNopPqstTuwWxXzZ]))",
    longer_alt=Identifier,
)


# --- mode token orderings (mirror of lexer.ts:74-147) ---------------------

_LANGUAGE: List[TokenType] = [
    Command,
    EndOfLine,
    WhiteSpace,
    SymbolLiteral,
    DateTimeLiteral,
    TimeStampLiteral,
    DateLiteral,
    MonthLiteral,
    TimeLiteral,
    InfinityLiteral,
    BinaryLiteral,
    ByteLiteral,
    NumberLiteral,
    System,
    Control,
    LSql,
    RSql,
    Keyword,
    Reserved,
    Identifier,
    CutDrop,
    Iterator,
    Comparator,
    DoubleColon,
    Dict,
    Operator,
    Cond,
    Colon,
    SemiColon,
    LParen,
    RParen,
    LBracket,
    RBracket,
    LCurly,
    RCurly,
]

MODES = {
    "q_mode": [
        CommentBegin,
        ExitCommentBegin,
        Documentation,
        LineComment,
        StringBegin,
        TestBegin,
        *_LANGUAGE,
    ],
    "test_mode": [
        CommentBegin,
        ExitCommentBegin,
        Documentation,
        LineComment,
        StringBegin,
        TestBlock,
        TestLambdaBlock,
        *_LANGUAGE,
    ],
    "string_mode": [StringEscape, StringEnd, EndOfLine, WhiteSpace, CharLiteral],
    "comment_mode": [CommentEnd, CommentEndOfLine, WhiteSpace, CommentLiteral],
    "exit_comment_mode": [CommentEndOfLine, WhiteSpace, CommentLiteral],
}

DEFAULT_MODE = "q_mode"
