"""Monitor rules as written in Lua: `hl.monitor({ output = ..., mode = ..., ... })`."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from typing import Any, Union


@dataclass(frozen=True)
class LuaRaw:
    """A Lua expression kept verbatim because it is not a literal we can interpret."""

    source: str


@dataclass
class LuaTable:
    """A Lua table constructor; entries keep their order and key style (`None` key = positional)."""

    entries: list[tuple[str | int | None, Any]] = field(default_factory=list)


LuaValue = Union[str, int, float, bool, None, LuaRaw, LuaTable]

# Field order used when writing a rule; anything else is kept in `extra`.
KNOWN_FIELDS = ("output", "mode", "position", "scale", "transform", "mirror", "bitdepth", "vrr", "cm", "disabled")


@dataclass
class MonitorRule:
    """One `hl.monitor` call. A field set to None was not specified in the config."""

    output: LuaValue = ""
    mode: LuaValue = None
    position: LuaValue = None
    scale: LuaValue = None
    transform: LuaValue = None
    mirror: LuaValue = None
    bitdepth: LuaValue = None
    vrr: LuaValue = None
    cm: LuaValue = None
    disabled: LuaValue = None
    extra: dict[str, LuaValue] = field(default_factory=dict)

    @classmethod
    def from_fields(cls, pairs: dict[str, LuaValue]) -> MonitorRule:
        known = {k: v for k, v in pairs.items() if k in KNOWN_FIELDS}
        extra = {k: v for k, v in pairs.items() if k not in KNOWN_FIELDS}
        return cls(**known, extra=extra)

    def to_fields(self) -> list[tuple[str, LuaValue]]:
        """Specified fields in canonical order, followed by unknown fields in source order."""
        out = [(name, getattr(self, name)) for name in KNOWN_FIELDS if getattr(self, name) is not None]
        return out + list(self.extra.items())

    @property
    def output_name(self) -> str:
        return self.output if isinstance(self.output, str) else ""

    @property
    def is_fallback(self) -> bool:
        return self.output == ""

    @property
    def is_disabled(self) -> bool:
        return self.disabled is True

    def copy(self) -> MonitorRule:
        values = {f.name: getattr(self, f.name) for f in fields(self)}
        values["extra"] = dict(self.extra)
        return MonitorRule(**values)


# --- typed views over raw Lua values -------------------------------------------------

_POSITION_RE = re.compile(r"^\s*(-?\d+)\s*x\s*(-?\d+)\s*$")
AUTO_POSITIONS = (
    "auto",
    "auto-right",
    "auto-left",
    "auto-up",
    "auto-down",
    "auto-center-right",
    "auto-center-left",
    "auto-center-up",
    "auto-center-down",
)


def parse_position(value: LuaValue) -> tuple[int, int] | None:
    """Explicit `XxY` positions as integers; None for `auto*` or anything unparseable."""
    if not isinstance(value, str):
        return None
    match = _POSITION_RE.match(value)
    return (int(match.group(1)), int(match.group(2))) if match else None


def format_position(x: int, y: int) -> str:
    return f"{int(x)}x{int(y)}"


def parse_scale(value: LuaValue) -> float | str | None:
    """A numeric scale, the string "auto", or None when unspecified/unparseable.

    Hyprland accepts scales as numbers or strings ("1.2"), so both are handled.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text == "auto":
            return "auto"
        try:
            return float(text)
        except ValueError:
            return None
    return None


def parse_int(value: LuaValue) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and float(value).is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None
