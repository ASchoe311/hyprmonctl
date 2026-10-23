"""The freedesktop launcher entry (`hyprmonctl install-desktop`).

Installing it adds "Displays" to app launchers and lets the desktop portal resolve the
window's app id (`hyprmonctl`), which Qt registers on startup.
"""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path

APP_ID = "hyprmonctl"


def entry_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "applications" / f"{APP_ID}.desktop"


def launch_command() -> str:
    """How to start the GUI, preferring the `hyprmonctl` being run right now."""
    current = Path(sys.argv[0])
    if current.name == APP_ID and current.exists():
        return f"{shlex.quote(str(current.resolve()))} gui"
    found = shutil.which(APP_ID)
    if found:
        return f"{shlex.quote(found)} gui"
    return f"{shlex.quote(sys.executable)} -m hyprmonctl gui"


def render_entry(command: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Displays\n"
        "GenericName=Monitor Settings\n"
        "Comment=Arrange monitors and set resolution, scale and rotation for Hyprland\n"
        f"Exec={command}\n"
        "Icon=preferences-desktop-display\n"
        "Terminal=false\n"
        "Categories=Settings;HardwareSettings;\n"
        "Keywords=monitor;display;resolution;scale;hyprland;\n"
        f"StartupWMClass={APP_ID}\n"
    )


def install() -> Path:
    path = entry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_entry(launch_command()), encoding="utf-8")
    return path
