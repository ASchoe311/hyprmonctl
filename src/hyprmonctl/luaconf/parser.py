"""Extract `hl.monitor({...})` rules from a Lua config file.

Only top-level calls with literal table arguments are understood. Any other code is
skipped and reported in `ParsedConfig.foreign_lines`, so callers can warn before the
file is regenerated. Non-literal field values are preserved verbatim as `LuaRaw`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from hyprmonctl.luaconf.lexer import LuaSyntaxError, Tok, Token, tokenize
from hyprmonctl.model.rule import LuaRaw, LuaTable, LuaValue, MonitorRule

_BLOCK_OPEN = {"function", "do", "if", "repeat"}
_BLOCK_CLOSE = {"end", "until"}
_BRACKETS = {"(": ")", "{": "}", "[": "]"}


@dataclass
class ParsedConfig:
    rules: list[MonitorRule] = field(default_factory=list)
    rule_lines: list[int] = field(default_factory=list)
    foreign_lines: list[int] = field(default_factory=list)
    error: LuaSyntaxError | None = None


def parse_source(source: str) -> ParsedConfig:
    try:
        return _Parser(source, tokenize(source)).parse()
    except LuaSyntaxError as exc:
        return ParsedConfig(error=exc)


def parse_file(path: Path) -> ParsedConfig:
    return parse_source(path.read_text(encoding="utf-8"))


def content_hash(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()[:16]


class _Parser:
    def __init__(self, source: str, tokens: list[Token]) -> None:
        self.src = source
        self.toks = tokens
        self.i = 0

    @property
    def tok(self) -> Token:
        return self.toks[self.i]

    def _peek(self, offset: int) -> Token:
        return self.toks[min(self.i + offset, len(self.toks) - 1)]

    def _expect_symbol(self, text: str) -> Token:
        if not self.tok.is_symbol(text):
            raise LuaSyntaxError(f"expected '{text}' near {self.tok.value!r}", self.tok.line)
        tok = self.tok
        self.i += 1
        return tok

    def parse(self) -> ParsedConfig:
        result = ParsedConfig()
        while self.tok.kind is not Tok.EOF:
            if self.tok.is_symbol(";"):
                self.i += 1
            elif self._at_monitor_call():
                line = self.tok.line
                result.rules.append(self._monitor_call())
                result.rule_lines.append(line)
            else:
                result.foreign_lines.append(self.tok.line)
                self._skip_foreign_statement()
        return result

    def _at_monitor_call(self) -> bool:
        return (
            self.tok.is_name("hl")
            and self._peek(1).is_symbol(".")
            and self._peek(2).is_name("monitor")
            and (self._peek(3).is_symbol("(") or self._peek(3).is_symbol("{"))
        )

    def _monitor_call(self) -> MonitorRule:
        self.i += 3
        parenthesized = self.tok.is_symbol("(")
        if parenthesized:
            self.i += 1
        table = self._table()
        if parenthesized:
            self._expect_symbol(")")
        named: dict[str, LuaValue] = {}
        for key, value in table.entries:
            if not isinstance(key, str):
                raise LuaSyntaxError("hl.monitor table must only contain named fields", self.tok.line)
            named[key] = value
        return MonitorRule.from_fields(named)

    def _table(self) -> LuaTable:
        self._expect_symbol("{")
        table = LuaTable()
        while not self.tok.is_symbol("}"):
            if self.tok.kind is Tok.NAME and self._peek(1).is_symbol("="):
                key: str | int | None = self.tok.value
                self.i += 2
            elif self.tok.is_symbol("["):
                self.i += 1
                key_tok = self.tok
                if key_tok.kind not in (Tok.STRING, Tok.NUMBER):
                    raise LuaSyntaxError("only literal table keys are supported", key_tok.line)
                key = key_tok.value
                self.i += 1
                self._expect_symbol("]")
                self._expect_symbol("=")
            else:
                key = None
            table.entries.append((key, self._value()))
            if self.tok.is_symbol(",") or self.tok.is_symbol(";"):
                self.i += 1
            elif not self.tok.is_symbol("}"):
                raise LuaSyntaxError(f"expected ',' or '}}' near {self.tok.value!r}", self.tok.line)
        self.i += 1
        return table

    def _value(self) -> LuaValue:
        tok, nxt = self.tok, self._peek(1)
        terminates = nxt.is_symbol(",") or nxt.is_symbol(";") or nxt.is_symbol("}")
        if tok.is_symbol("{"):
            return self._table()
        if terminates and tok.kind in (Tok.STRING, Tok.NUMBER):
            self.i += 1
            return tok.value
        if terminates and tok.kind is Tok.NAME and tok.value in ("true", "false", "nil"):
            self.i += 1
            return {"true": True, "false": False, "nil": None}[tok.value]
        if tok.is_symbol("-") and nxt.kind is Tok.NUMBER and self._is_value_end(self._peek(2)):
            self.i += 2
            return -nxt.value
        return self._raw_expression()

    @staticmethod
    def _is_value_end(tok: Token) -> bool:
        return tok.is_symbol(",") or tok.is_symbol(";") or tok.is_symbol("}")

    def _raw_expression(self) -> LuaRaw:
        start = self.tok.start
        depth = 0
        end = start
        while self.tok.kind is not Tok.EOF:
            if depth == 0 and self._is_value_end(self.tok):
                break
            if self.tok.kind is Tok.SYMBOL and self.tok.value in _BRACKETS:
                depth += 1
            elif self.tok.kind is Tok.SYMBOL and self.tok.value in _BRACKETS.values():
                depth -= 1
            elif self.tok.kind is Tok.NAME and self.tok.value in _BLOCK_OPEN:
                depth += 1
            elif self.tok.kind is Tok.NAME and self.tok.value in _BLOCK_CLOSE:
                depth -= 1
            end = self.tok.end
            self.i += 1
        if end == start:
            raise LuaSyntaxError("expected a value", self.tok.line)
        return LuaRaw(self.src[start:end].strip())

    def _skip_foreign_statement(self) -> None:
        """Skip tokens until the next top-level `hl.monitor` call (or EOF)."""
        depth = 0
        first = True
        while self.tok.kind is not Tok.EOF:
            if depth == 0 and not first and self._at_monitor_call():
                return
            first = False
            tok = self.tok
            if tok.kind is Tok.SYMBOL and tok.value in _BRACKETS:
                depth += 1
            elif tok.kind is Tok.SYMBOL and tok.value in _BRACKETS.values():
                depth -= 1
            elif tok.kind is Tok.NAME and tok.value in _BLOCK_OPEN:
                depth += 1
            elif tok.kind is Tok.NAME and tok.value in _BLOCK_CLOSE:
                depth -= 1
            self.i += 1
