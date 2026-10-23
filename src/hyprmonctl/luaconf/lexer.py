"""A tokenizer for Lua source, sufficient to read and skip arbitrary Lua 5.x code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class LuaSyntaxError(ValueError):
    def __init__(self, message: str, line: int) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line


class Tok(Enum):
    NAME = "name"
    STRING = "string"
    NUMBER = "number"
    SYMBOL = "symbol"
    EOF = "eof"


@dataclass(frozen=True)
class Token:
    kind: Tok
    value: object  # str for NAME/SYMBOL/STRING, int|float for NUMBER
    start: int  # offset in source
    end: int
    line: int

    def is_symbol(self, text: str) -> bool:
        return self.kind is Tok.SYMBOL and self.value == text

    def is_name(self, text: str) -> bool:
        return self.kind is Tok.NAME and self.value == text


_SYMBOLS = ("...", "..", "==", "~=", "<=", ">=", "<<", ">>", "//", "::") + tuple("+-*/%^#&~|<>=(){}[];:,.")
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER_RE = re.compile(
    r"0[xX](?:[0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?|\.[0-9a-fA-F]+)(?:[pP][+-]?\d+)?"
    r"|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
)
_LONG_OPEN_RE = re.compile(r"\[(=*)\[")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\\": "\\", '"': '"', "'": "'", "\n": "\n"}


def tokenize(source: str) -> list[Token]:
    return list(_Lexer(source).tokens())


class _Lexer:
    def __init__(self, source: str) -> None:
        self.src = source
        self.pos = 0
        self.line = 1

    def tokens(self):
        while True:
            self._skip_space_and_comments()
            if self.pos >= len(self.src):
                yield Token(Tok.EOF, None, self.pos, self.pos, self.line)
                return
            yield self._next()

    def _advance(self, count: int) -> str:
        text = self.src[self.pos : self.pos + count]
        self.line += text.count("\n")
        self.pos += count
        return text

    def _skip_space_and_comments(self) -> None:
        src = self.src
        while self.pos < len(src):
            ch = src[self.pos]
            if ch in " \t\r\n\f\v":
                self._advance(1)
            elif src.startswith("--", self.pos):
                self._advance(2)
                long = _LONG_OPEN_RE.match(src, self.pos)
                if long:
                    self._read_long_bracket(long)
                else:
                    end = src.find("\n", self.pos)
                    self._advance((len(src) if end < 0 else end) - self.pos)
            else:
                return

    def _read_long_bracket(self, opener: re.Match[str]) -> str:
        close = "]" + opener.group(1) + "]"
        start_line = self.line
        self._advance(len(opener.group(0)))
        end = self.src.find(close, self.pos)
        if end < 0:
            raise LuaSyntaxError("unfinished long string/comment", start_line)
        body = self._advance(end - self.pos)
        self._advance(len(close))
        return body[1:] if body.startswith("\n") else body

    def _next(self) -> Token:
        src, start, line = self.src, self.pos, self.line
        ch = src[start]

        if ch.isalpha() or ch == "_":
            name = _NAME_RE.match(src, start).group(0)
            self._advance(len(name))
            return Token(Tok.NAME, name, start, self.pos, line)

        if ch.isdigit() or (ch == "." and start + 1 < len(src) and src[start + 1].isdigit()):
            text = _NUMBER_RE.match(src, start).group(0)
            self._advance(len(text))
            return Token(Tok.NUMBER, _number_value(text), start, self.pos, line)

        if ch in "\"'":
            return Token(Tok.STRING, self._read_quoted(ch), start, self.pos, line)

        if ch == "[":
            long = _LONG_OPEN_RE.match(src, start)
            if long:
                return Token(Tok.STRING, self._read_long_bracket(long), start, self.pos, line)

        for symbol in _SYMBOLS:
            if src.startswith(symbol, start):
                self._advance(len(symbol))
                return Token(Tok.SYMBOL, symbol, start, self.pos, line)

        raise LuaSyntaxError(f"unexpected character {ch!r}", line)

    def _read_quoted(self, quote: str) -> str:
        src, start_line = self.src, self.line
        self._advance(1)
        out: list[str] = []
        while True:
            if self.pos >= len(src) or src[self.pos] == "\n":
                raise LuaSyntaxError("unfinished string", start_line)
            ch = self._advance(1)
            if ch == quote:
                return "".join(out)
            if ch != "\\":
                out.append(ch)
                continue
            esc = self._advance(1)
            if esc in _ESCAPES:
                out.append(_ESCAPES[esc])
            elif esc == "z":
                while self.pos < len(src) and src[self.pos].isspace():
                    self._advance(1)
            elif esc == "x":
                out.append(chr(int(self._advance(2), 16)))
            elif esc.isdigit():
                digits = esc
                while len(digits) < 3 and self.pos < len(src) and src[self.pos].isdigit():
                    digits += self._advance(1)
                out.append(chr(int(digits)))
            elif esc == "u" and src.startswith("{", self.pos):
                end = src.index("}", self.pos)
                out.append(chr(int(self._advance(end - self.pos + 1)[1:-1], 16)))
            else:
                raise LuaSyntaxError(f"invalid escape \\{esc}", self.line)


def _number_value(text: str) -> int | float:
    lower = text.lower()
    if lower.startswith("0x"):
        if "." in lower or "p" in lower:
            return float.fromhex(text)
        return int(text, 16)
    if any(c in lower for c in ".e"):
        return float(text)
    return int(text)
