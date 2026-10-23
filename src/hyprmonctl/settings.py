"""Persistent application settings (`~/.config/hyprmonctl/settings.json`)."""

from __future__ import annotations

import dataclasses
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hyprmonctl import paths
from hyprmonctl.luaconf.discovery import default_lua_path
from hyprmonctl.serialize import camel, snake, to_json

DEFAULT_THEME_COLORS = "~/.local/state/quickshell/user/generated/colors.json"


@dataclass
class Settings:
    lua_path: str
    confirm_timeout: int = 15
    reload_after_save: bool = True
    backup: bool = True
    theme_colors_path: str = DEFAULT_THEME_COLORS
    snap_distance: int = 16

    @property
    def resolved_lua_path(self) -> Path:
        return paths.expand(self.lua_path)


def _validate(key: str, value: Any) -> Any:
    if key == "lua_path":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("luaPath must be a non-empty path")
        if not value.strip().endswith(".lua"):
            raise ValueError("luaPath must point to a .lua file")
        return value.strip()
    if key in ("reload_after_save", "backup"):
        if not isinstance(value, bool):
            raise ValueError(f"{camel(key)} must be true or false")
        return value
    if key == "theme_colors_path":
        if not isinstance(value, str):
            raise ValueError("themeColorsPath must be a string (empty disables theming)")
        return value.strip()
    if key in ("confirm_timeout", "snap_distance"):
        low, high = (5, 300) if key == "confirm_timeout" else (0, 200)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError(f"{camel(key)} must be a number between {low} and {high}")
        return int(value)
    raise ValueError(f"unknown setting {camel(key)!r}")


_FIELDS = tuple(f.name for f in dataclasses.fields(Settings))


class SettingsStore:
    """Defaults, overlaid with the settings file, overlaid with per-process overrides."""

    def __init__(self, path: Path | None = None, overrides: dict[str, Any] | None = None) -> None:
        self.path = path or paths.settings_file()
        self._overrides = {snake(k): _validate(snake(k), v) for k, v in (overrides or {}).items()}
        self._lock = threading.Lock()

    def _stored(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        stored = {}
        for key, value in raw.items() if isinstance(raw, dict) else ():
            try:
                stored[snake(key)] = _validate(snake(key), value)
            except ValueError:
                continue  # ignore stale or hand-broken entries rather than failing to start
        return stored

    def load(self) -> Settings:
        values = {**self._stored(), **self._overrides}
        values.setdefault("lua_path", paths.contract(default_lua_path()))
        return Settings(**{k: v for k, v in values.items() if k in _FIELDS})

    def update(self, patch: dict[str, Any]) -> Settings:
        cleaned = {snake(k): _validate(snake(k), v) for k, v in patch.items()}
        with self._lock:
            for key in cleaned:  # an explicit change supersedes a command-line override
                self._overrides.pop(key, None)
            stored = {**self._stored(), **cleaned}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(to_json(stored), indent=2) + "\n", encoding="utf-8")
        return self.load()
