"""Live monitor state as reported by Hyprland (`hyprctl monitors all -j`)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

INTERNAL_PORT_PREFIXES = ("eDP", "LVDS", "DSI")

_MODE_RE = re.compile(r"^\s*(\d+)\s*x\s*(\d+)\s*(?:@\s*([\d.]+)\s*(?:Hz)?)?\s*$", re.IGNORECASE)


@dataclass(frozen=True, order=True)
class Mode:
    width: int
    height: int
    refresh: float = 0.0  # Hz; 0 means "unspecified"

    @classmethod
    def parse(cls, text: str) -> Mode | None:
        """Parse `1920x1080`, `1920x1080@60` or hyprctl's `1920x1080@60.00Hz`."""
        match = _MODE_RE.match(text)
        if not match:
            return None
        width, height, refresh = match.groups()
        return cls(int(width), int(height), float(refresh) if refresh else 0.0)

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def area(self) -> int:
        return self.width * self.height

    def __str__(self) -> str:
        if not self.refresh:
            return self.resolution
        return f"{self.resolution}@{self.refresh:.2f}"


@dataclass
class MonitorInfo:
    id: int
    name: str
    description: str
    make: str
    model: str
    serial: str
    width: int
    height: int
    refresh_rate: float
    x: int
    y: int
    scale: float
    transform: int
    disabled: bool
    focused: bool = False
    mirror_of: str | None = None
    vrr: bool = False
    physical_width_mm: int = 0
    physical_height_mm: int = 0
    current_format: str = ""
    color_preset: str = ""
    available_modes: list[Mode] = field(default_factory=list)

    @classmethod
    def from_hyprctl(cls, data: dict[str, Any]) -> MonitorInfo:
        mirror = data.get("mirrorOf")
        return cls(
            id=int(data.get("id", -1)),
            name=data["name"],
            description=(data.get("description") or "").strip(),
            make=(data.get("make") or "").strip(),
            model=(data.get("model") or "").strip(),
            serial=(data.get("serial") or "").strip(),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            refresh_rate=float(data.get("refreshRate", 0.0)),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            scale=float(data.get("scale", 1.0)),
            transform=int(data.get("transform", 0)),
            disabled=bool(data.get("disabled", False)),
            focused=bool(data.get("focused", False)),
            mirror_of=None if mirror in (None, "", "none") else str(mirror),
            vrr=bool(data.get("vrr", False)),
            physical_width_mm=int(data.get("physicalWidth", 0)),
            physical_height_mm=int(data.get("physicalHeight", 0)),
            current_format=data.get("currentFormat", ""),
            color_preset=data.get("colorManagementPreset", ""),
            available_modes=dedupe_modes(data.get("availableModes", [])),
        )

    @property
    def is_internal(self) -> bool:
        return self.name.startswith(INTERNAL_PORT_PREFIXES)

    @property
    def short_description(self) -> str:
        return f"{self.make} {self.model}".strip()

    @property
    def bitdepth(self) -> int:
        return 10 if "2101010" in self.current_format else 8

    @property
    def diagonal_inches(self) -> float | None:
        if self.physical_width_mm <= 0 or self.physical_height_mm <= 0:
            return None
        return math.hypot(self.physical_width_mm, self.physical_height_mm) / 25.4

    @property
    def current_mode(self) -> Mode | None:
        if self.width > 0 and self.height > 0:
            return Mode(self.width, self.height, round(self.refresh_rate, 2))
        return self.available_modes[0] if self.available_modes else None

    @property
    def label(self) -> str:
        """Human label in the style of desktop display settings, e.g. `27.2" DP-1 external display`."""
        size = f'{self.diagonal_inches:.1f}" ' if self.diagonal_inches else ""
        if self.is_internal:
            return f"{size}laptop display"
        return f"{size}{self.name} external display"


def dedupe_modes(raw: list[str]) -> list[Mode]:
    """Parse hyprctl's mode strings, dropping duplicates while keeping driver order."""
    seen: set[Mode] = set()
    modes: list[Mode] = []
    for text in raw:
        mode = Mode.parse(text)
        if mode and mode not in seen:
            seen.add(mode)
            modes.append(mode)
    return modes


def resolutions(modes: list[Mode]) -> list[tuple[int, int, list[float]]]:
    """Group modes by resolution (largest first) with refresh rates sorted descending."""
    grouped: dict[tuple[int, int], set[float]] = {}
    for mode in modes:
        grouped.setdefault((mode.width, mode.height), set()).add(mode.refresh)
    ordered = sorted(grouped.items(), key=lambda item: (item[0][0] * item[0][1], item[0][0]), reverse=True)
    return [(w, h, sorted(rates, reverse=True)) for (w, h), rates in ordered]


SPECIAL_MODES = ("preferred", "highres", "highrr", "maxwidth")


def resolve_special_mode(name: str, modes: list[Mode]) -> Mode | None:
    """Resolve Hyprland's symbolic modes against the modes a monitor advertises."""
    if not modes:
        return None
    if name == "preferred":
        return modes[0]
    if name == "highres":
        return max(modes, key=lambda m: (m.area, m.refresh))
    if name == "highrr":
        return max(modes, key=lambda m: (m.refresh, m.area))
    if name == "maxwidth":
        return max(modes, key=lambda m: (m.width, m.area, m.refresh))
    return None
