"""Find where monitor rules live by inspecting `require(...)` calls in hyprland.lua."""

from __future__ import annotations

import re
from pathlib import Path

from hyprmonctl import paths

_REQUIRE_RE = re.compile(r"""\brequire\s*\(?\s*(["'])([\w./-]+)\1""")


def required_modules(main_config: Path) -> list[str]:
    try:
        text = main_config.read_text(encoding="utf-8")
    except OSError:
        return []
    return [match.group(2) for match in _REQUIRE_RE.finditer(text)]


def module_path(module: str, base: Path) -> Path:
    """Map a Lua module name (`config.monitors`) to its file under the Hyprland config dir."""
    return base / (module.replace(".", "/") + ".lua")


def module_name(path: Path, base: Path) -> str | None:
    """The `require` name for a file under `base`, or None if it is outside it."""
    try:
        relative = path.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    return ".".join(relative.with_suffix("").parts)


def default_lua_path(main_config: Path | None = None) -> Path:
    """First required module mentioning "monitor", else `~/.config/hypr/monitors.lua`."""
    main_config = main_config or paths.hypr_main_config()
    base = main_config.parent
    for module in required_modules(main_config):
        if "monitor" in module.lower():
            return module_path(module, base)
    return base / "monitors.lua"


def is_required(lua_path: Path, main_config: Path | None = None) -> bool | None:
    """Whether hyprland.lua requires `lua_path`; None when hyprland.lua can't be read."""
    main_config = main_config or paths.hypr_main_config()
    if not main_config.is_file():
        return None
    if lua_path.resolve() == main_config.resolve():
        return True
    name = module_name(lua_path, main_config.parent)
    return name is not None and name in required_modules(main_config)
