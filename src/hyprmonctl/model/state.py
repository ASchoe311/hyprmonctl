"""Data shapes exchanged with clients (serialized to camelCase JSON by `serialize.to_json`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyprmonctl.model.identity import IdentifierCandidate

TRANSFORMS = range(8)


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    monitors: list[str] = field(default_factory=list)


@dataclass
class MonitorConfig:
    """The editable settings for one connected monitor; becomes one `hl.monitor` rule."""

    name: str
    output: str
    enabled: bool = True
    mode: str = "preferred"
    position: str = "auto"
    scale: float | str = "auto"
    transform: int = 0
    mirror: str | None = None
    bitdepth: int | None = None
    vrr: int | None = None
    cm: str | None = None
    rule_index: int | None = None  # file rule this config derives from (its extra fields are kept)

    @classmethod
    def from_json(cls, data: Any) -> MonitorConfig:
        if not isinstance(data, dict):
            raise ValueError("monitor config must be an object")

        def get(key: str, kinds: tuple[type, ...], default: Any = None, required: bool = False) -> Any:
            value = data.get(key, default)
            if value is None and not required:
                return default
            if (isinstance(value, bool) and bool not in kinds) or not isinstance(value, kinds):
                raise ValueError(f"monitor config field {key!r} has an invalid value: {value!r}")
            return value

        scale = get("scale", (int, float, str), "auto")
        if isinstance(scale, str) and scale != "auto":
            raise ValueError(f"scale must be a number or \"auto\", got {scale!r}")
        transform = get("transform", (int,), 0)
        if transform not in TRANSFORMS:
            raise ValueError(f"transform must be 0-7, got {transform}")
        return cls(
            name=get("name", (str,), required=True),
            output=get("output", (str,), required=True),
            enabled=get("enabled", (bool,), True),
            mode=get("mode", (str,), "preferred") or "preferred",
            position=get("position", (str,), "auto") or "auto",
            scale=float(scale) if isinstance(scale, (int, float)) else scale,
            transform=transform,
            mirror=get("mirror", (str,)) or None,
            bitdepth=get("bitdepth", (int,)),
            vrr=get("vrr", (int,)),
            cm=get("cm", (str,)) or None,
            rule_index=get("ruleIndex", (int,)),
        )


@dataclass
class Draft:
    """A complete proposed configuration: connected monitors plus the file rules to keep."""

    monitors: list[MonitorConfig]
    keep_rules: list[int] = field(default_factory=list)
    file_hash: str | None = None

    @classmethod
    def from_json(cls, data: Any) -> Draft:
        if not isinstance(data, dict) or not isinstance(data.get("monitors"), list):
            raise ValueError("draft must be an object with a 'monitors' list")
        keep = data.get("keepRules", [])
        if not isinstance(keep, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in keep):
            raise ValueError("keepRules must be a list of rule indices")
        file_hash = data.get("fileHash")
        if file_hash is not None and not isinstance(file_hash, str):
            raise ValueError("fileHash must be a string")
        return cls([MonitorConfig.from_json(m) for m in data["monitors"]], keep, file_hash)


@dataclass
class ResolutionInfo:
    width: int
    height: int
    refresh_rates: list[float]
    scales: list[float]  # every valid scale for this resolution
    nice_scales: list[float]  # the subset offered as coarse choices


@dataclass
class LiveState:
    x: int
    y: int
    width: int
    height: int
    refresh_rate: float
    scale: float
    transform: int
    disabled: bool
    mirror_of: str | None
    vrr: bool
    bitdepth: int
    color_preset: str
    logical_width: int
    logical_height: int


@dataclass
class MonitorEntry:
    id: int
    name: str
    description: str
    make: str
    model: str
    serial: str
    label: str
    internal: bool
    focused: bool
    diagonal_inches: float | None
    live: LiveState
    resolutions: list[ResolutionInfo]
    special_modes: dict[str, str]
    identifiers: list[IdentifierCandidate]
    default_identifier: str
    matched_by_fallback: bool
    config: MonitorConfig


@dataclass
class SavedRule:
    """A rule in the file that does not configure any connected monitor."""

    index: int
    output: str
    status: str  # "disconnected" | "fallback" | "overridden"
    mode: str | None
    position: str | None
    scale: str | None
    disabled: bool
    lua: str


@dataclass
class PreviewInfo:
    deadline: float  # unix time at which the preview reverts automatically
    timeout: int


@dataclass
class Placement:
    name: str
    x: int
    y: int
    width: int
    height: int


@dataclass
class ValidationResult:
    issues: list[Issue]
    placements: list[Placement]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]


@dataclass
class SaveResult:
    path: str
    backup_path: str | None
    file_hash: str | None
    config_errors: list[str]


@dataclass
class AppState:
    api_version: int
    lua_path: str
    lua_path_display: str
    lua_module: str | None
    file_exists: bool
    file_hash: str | None
    monitors: list[MonitorEntry]
    saved_rules: list[SavedRule]
    diagnostics: list[Issue]
    settings: Any
    preview: PreviewInfo | None
