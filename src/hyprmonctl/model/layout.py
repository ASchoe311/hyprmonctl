"""Geometry of the virtual monitor layout (logical pixels)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def overlaps(self, other: Rect) -> bool:
        """True when the rectangles share area (touching edges do not count)."""
        return self.x < other.right and other.x < self.right and self.y < other.bottom and other.y < self.bottom

    def touches(self, other: Rect) -> bool:
        """True when the rectangles share a stretch of edge, so the cursor can cross between them."""
        vertical_edge = (self.right == other.x or other.right == self.x) and min(self.bottom, other.bottom) > max(
            self.y, other.y
        )
        horizontal_edge = (self.bottom == other.y or other.bottom == self.y) and min(self.right, other.right) > max(
            self.x, other.x
        )
        return vertical_edge or horizontal_edge


def logical_size(width: int, height: int, scale: float, transform: int = 0) -> tuple[int, int]:
    """Size a mode occupies in the layout once scaled and rotated."""
    scale = scale if scale > 0 else 1.0
    w, h = round(width / scale), round(height / scale)
    return (h, w) if transform % 2 == 1 else (w, h)


def find_overlaps(rects: dict[str, Rect]) -> list[tuple[str, str]]:
    names = list(rects)
    return [
        (a, b)
        for i, a in enumerate(names)
        for b in names[i + 1 :]
        if rects[a].overlaps(rects[b])
    ]


def find_detached(rects: dict[str, Rect]) -> list[str]:
    """Monitors that share no edge with any other monitor (only meaningful with 2+ monitors).

    Overlapping monitors are not reported here; that is a separate, more serious problem.
    """
    if len(rects) < 2:
        return []
    return [
        name
        for name, rect in rects.items()
        if not any(rect.touches(other) or rect.overlaps(other) for other_name, other in rects.items() if other_name != name)
    ]
