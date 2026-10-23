"""Render monitor rules back to Lua source."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

from hyprmonctl.model.rule import LuaRaw, LuaTable, LuaValue, MonitorRule
from hyprmonctl.model.scale import format_scale

HEADER = (
    "-- Monitor configuration, managed by hyprmonctl.\n"
    "-- Docs: https://wiki.hypr.land/Configuring/Basics/Monitors/\n"
    "-- Edits made here are kept, but comments are not preserved when hyprmonctl saves.\n"
)

INDENT = "    "
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LUA_KEYWORDS = frozenset(
    "and break do else elseif end false for function goto if in local nil not or repeat return then true until while".split()
)


def render_value(value: LuaValue) -> str:
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format_scale(value)
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, LuaRaw):
        return value.source
    if isinstance(value, LuaTable):
        return _render_table(value)
    raise TypeError(f"cannot render {type(value).__name__} as Lua")


def _quote(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _key_text(key: str | int) -> str:
    if isinstance(key, str) and _IDENTIFIER_RE.match(key) and key not in _LUA_KEYWORDS:
        return key
    return f"[{render_value(key)}]"


def _render_table(table: LuaTable) -> str:
    if not table.entries:
        return "{}"
    parts = [render_value(v) if k is None else f"{_key_text(k)} = {render_value(v)}" for k, v in table.entries]
    return "{ " + ", ".join(parts) + " }"


def render_rule(rule: MonitorRule) -> str:
    """A multi-line `hl.monitor({...})` block with aligned `=` signs."""
    pairs = rule.to_fields()
    keys = [_key_text(k) for k, _ in pairs]
    width = max(map(len, keys), default=0)
    lines = [f"{INDENT}{key.ljust(width)} = {render_value(value)}," for key, (_, value) in zip(keys, pairs)]
    return "hl.monitor({\n" + "\n".join(lines) + "\n})\n"


def render_call(rule: MonitorRule) -> str:
    """A single-line `hl.monitor({...})` call, suitable for `hyprctl eval`."""
    body = ", ".join(f"{_key_text(k)} = {render_value(v)}" for k, v in rule.to_fields())
    return f"hl.monitor({{ {body} }})"


def render_file(rules: Sequence[MonitorRule]) -> str:
    return HEADER + "".join("\n" + render_rule(rule) for rule in rules)


def write_atomic(path: Path, text: str, backup: bool = True) -> Path | None:
    """Write `text` to `path` atomically; returns the backup path if one was made."""
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if backup and path.exists():
        backup_path = path.with_name(path.name + ".bak")
        shutil.copy2(path, backup_path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        if path.exists():
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return backup_path
