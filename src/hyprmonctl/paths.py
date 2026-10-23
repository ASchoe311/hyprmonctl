"""Filesystem locations used by hyprmonctl."""

from __future__ import annotations

import os
from pathlib import Path


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def hypr_config_dir() -> Path:
    return xdg_config_home() / "hypr"


def hypr_main_config() -> Path:
    return hypr_config_dir() / "hyprland.lua"


def settings_file() -> Path:
    return xdg_config_home() / "hyprmonctl" / "settings.json"


def qml_dir() -> Path:
    """Directory that must be on the QML import path to `import HyprMonCtl`."""
    return Path(__file__).parent / "qml"


def expand(path: str | os.PathLike[str]) -> Path:
    """Expand `~` and environment variables in a user-supplied path."""
    return Path(os.path.expandvars(os.path.expanduser(os.fspath(path))))


def contract(path: Path) -> str:
    """Render a path with the home directory abbreviated to `~`."""
    home = Path.home()
    try:
        return "~/" + str(path.relative_to(home))
    except ValueError:
        return str(path)
