"""How a rule's `output` string selects a monitor, mirroring Hyprland's semantics.

- `desc:<text>` matches when the monitor description (or "make model") starts with <text>.
- Any other non-empty string must equal the connector name (e.g. `DP-1`).
- An empty string is the fallback rule, used only when nothing else matches.
- When several rules match, the one defined last wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from hyprmonctl.model.monitor import MonitorInfo
from hyprmonctl.model.rule import MonitorRule

DESC_PREFIX = "desc:"


@dataclass(frozen=True)
class RuleMatch:
    index: int
    fallback: bool = False


@dataclass(frozen=True)
class IdentifierCandidate:
    value: str
    kind: str  # "descFull" | "descModel" | "port"
    label: str
    unique: bool


def matches(output: str, monitor: MonitorInfo) -> bool:
    if not output:
        return False
    if output.startswith(DESC_PREFIX):
        wanted = output[len(DESC_PREFIX) :].strip()
        if not wanted:
            return False
        return monitor.description.startswith(wanted) or monitor.short_description.startswith(wanted)
    return output == monitor.name


def matching_monitors(output: str, monitors: Sequence[MonitorInfo]) -> list[MonitorInfo]:
    return [m for m in monitors if matches(output, m)]


def resolve_rule(rules: Sequence[MonitorRule], monitor: MonitorInfo) -> RuleMatch | None:
    for index in range(len(rules) - 1, -1, -1):
        if matches(rules[index].output_name, monitor):
            return RuleMatch(index)
    for index, rule in enumerate(rules):
        if rule.is_fallback:
            return RuleMatch(index, fallback=True)
    return None


def candidates(monitor: MonitorInfo, connected: Sequence[MonitorInfo]) -> list[IdentifierCandidate]:
    """Identifier choices for a monitor, most specific first."""

    def unique(value: str) -> bool:
        return [m.name for m in matching_monitors(value, connected)] == [monitor.name]

    out: list[IdentifierCandidate] = []
    if monitor.description:
        value = DESC_PREFIX + monitor.description
        label = "Description + serial" if monitor.serial else "Description"
        out.append(IdentifierCandidate(value, "descFull", label, unique(value)))
    if monitor.serial and monitor.short_description and monitor.short_description != monitor.description:
        value = DESC_PREFIX + monitor.short_description
        out.append(IdentifierCandidate(value, "descModel", "Make + model (any unit)", unique(value)))
    out.append(IdentifierCandidate(monitor.name, "port", "Connector", unique(monitor.name)))
    return out


def default_identifier(monitor: MonitorInfo, connected: Sequence[MonitorInfo]) -> str:
    """The most unique stable descriptor for a monitor.

    Ranking: description with serial > built-in panel connector (eDP/LVDS/DSI) >
    description when unique among connected monitors > connector name.
    """
    by_kind = {c.kind: c for c in candidates(monitor, connected)}
    full = by_kind.get("descFull")
    if monitor.serial and full and full.unique:
        return full.value
    if monitor.is_internal:
        return monitor.name
    if full and full.unique:
        return full.value
    return monitor.name
