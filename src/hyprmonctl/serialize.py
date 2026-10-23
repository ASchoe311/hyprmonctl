"""Conversion between Python dataclasses (snake_case) and JSON objects (camelCase)."""

from __future__ import annotations

import dataclasses
import re
from enum import Enum
from pathlib import Path
from typing import Any

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


def snake(name: str) -> str:
    return _CAMEL_BOUNDARY.sub("_", name).lower()


def to_json(value: Any) -> Any:
    """Recursively convert dataclasses/enums/paths into JSON-ready values with camelCase keys."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {camel(f.name): to_json(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {camel(k) if isinstance(k, str) else k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    return value
