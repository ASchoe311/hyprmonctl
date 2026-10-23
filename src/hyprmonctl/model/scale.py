"""Fractional scale math.

Hyprland only accepts scales that divide the mode into whole logical pixels, on the
1/120 grid used by the fractional-scale protocol (e.g. 1920x1200 @ 1.2 is valid,
@ 1.4 is not). These helpers enumerate and check such scales.
"""

from __future__ import annotations

import math

SCALE_DENOMINATOR = 120
MIN_SCALE = 0.5
MAX_SCALE = 4.0
# Scales offered as the coarse "base" choices in the UI, when valid for the mode.
NICE_STEP = 0.25


def _numerators(width: int, height: int, lo: float, hi: float) -> list[int]:
    if width <= 0 or height <= 0:
        return []
    common = math.gcd(width, height) * SCALE_DENOMINATOR
    start = math.ceil(lo * SCALE_DENOMINATOR)
    stop = math.floor(hi * SCALE_DENOMINATOR)
    return [k for k in range(start, stop + 1) if common % k == 0]


def valid_scales(width: int, height: int, lo: float = MIN_SCALE, hi: float = MAX_SCALE) -> list[float]:
    """All scales in [lo, hi] that give an integer logical size for `width`x`height`."""
    return [k / SCALE_DENOMINATOR for k in _numerators(width, height, lo, hi)]


def is_valid_scale(width: int, height: int, scale: float) -> bool:
    if scale <= 0 or width <= 0 or height <= 0:
        return False
    k = round(scale * SCALE_DENOMINATOR)
    if abs(scale * SCALE_DENOMINATOR - k) > 0.01 or k == 0:
        return False
    return (width * SCALE_DENOMINATOR) % k == 0 and (height * SCALE_DENOMINATOR) % k == 0


def nearest_valid_scale(width: int, height: int, scale: float) -> float | None:
    candidates = valid_scales(width, height)
    if not candidates:
        return None
    return min(candidates, key=lambda s: (abs(s - scale), s))


def nice_scales(width: int, height: int) -> list[float]:
    """Valid scales on the 25% grid; always includes 1.0."""
    step = round(NICE_STEP * SCALE_DENOMINATOR)
    nice = [s for s in valid_scales(width, height) if round(s * SCALE_DENOMINATOR) % step == 0]
    return nice or [1.0]


def format_scale(scale: float) -> str:
    """Compact decimal for Lua output: 1.0 -> "1", 4/3 -> "1.333333"."""
    text = f"{scale:.6f}".rstrip("0").rstrip(".")
    return text or "0"
