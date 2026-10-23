"""Translating between file rules, live monitors and editable drafts, and validating drafts."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

from hyprmonctl.model.identity import default_identifier, matches, matching_monitors, resolve_rule
from hyprmonctl.model.layout import Rect, find_detached, find_overlaps, logical_size
from hyprmonctl.model.monitor import SPECIAL_MODES, Mode, MonitorInfo, resolve_special_mode
from hyprmonctl.model.rule import MonitorRule, format_position, parse_int, parse_position, parse_scale
from hyprmonctl.model.scale import format_scale, is_valid_scale, nearest_valid_scale
from hyprmonctl.model.state import Draft, Issue, MonitorConfig, Placement, ValidationResult

# What Hyprland does for a monitor that no rule matches. Note the scale is 1, not "auto":
# auto picks by pixel density and can differ (e.g. headless outputs get 2).
DEFAULT_RULE = MonitorRule(mode="preferred", position="auto", scale=1.0)


# --- rules -> drafts -----------------------------------------------------------------


def config_from_rule(name: str, output: str, rule: MonitorRule, index: int | None) -> MonitorConfig:
    scale = parse_scale(rule.scale)
    return MonitorConfig(
        name=name,
        output=output,
        enabled=not rule.is_disabled,
        mode=rule.mode.strip() if isinstance(rule.mode, str) and rule.mode.strip() else "preferred",
        position=rule.position.strip() if isinstance(rule.position, str) and rule.position.strip() else "auto",
        scale=scale if scale is not None else "auto",
        transform=parse_int(rule.transform) or 0,
        mirror=rule.mirror if isinstance(rule.mirror, str) and rule.mirror else None,
        bitdepth=parse_int(rule.bitdepth),
        vrr=parse_int(rule.vrr),
        cm=rule.cm if isinstance(rule.cm, str) and rule.cm else None,
        rule_index=index,
    )


def owned_rule_indices(monitors: Sequence[MonitorInfo], rules: Sequence[MonitorRule]) -> dict[int, str]:
    """Rule index -> the connected monitor it configures (first by id when a rule is shared)."""
    owners: dict[int, str] = {}
    for monitor in sorted(monitors, key=lambda m: m.id):
        match = resolve_rule(rules, monitor)
        if match and not match.fallback:
            owners.setdefault(match.index, monitor.name)
    return owners


def initial_configs(monitors: Sequence[MonitorInfo], rules: Sequence[MonitorRule]) -> list[MonitorConfig]:
    """The draft that reproduces what the file currently says for each connected monitor.

    A monitor keeps the identifier of the rule that matches it. Monitors matched only by
    the fallback rule, or sharing a rule with another monitor, get their own identifier.
    """
    owners = owned_rule_indices(monitors, rules)
    configs = []
    for monitor in sorted(monitors, key=lambda m: m.id):
        match = resolve_rule(rules, monitor)
        if match is None:
            config = config_from_rule(monitor.name, default_identifier(monitor, monitors), DEFAULT_RULE, None)
            if not monitor.disabled:
                config.scale = round(monitor.scale, 6)  # nothing in the file says otherwise: keep what's shown
            configs.append(config)
            continue
        rule = rules[match.index]
        owns = not match.fallback and owners.get(match.index) == monitor.name
        output = rule.output_name if owns else default_identifier(monitor, monitors)
        configs.append(config_from_rule(monitor.name, output, rule, match.index))
    return configs


# --- drafts -> rules -----------------------------------------------------------------


def config_to_rule(config: MonitorConfig, base: MonitorRule | None) -> MonitorRule:
    """Build the rule for a config, carrying over fields hyprmonctl doesn't edit from `base`."""
    rule = MonitorRule(output=config.output, extra=dict(base.extra) if base else {})
    rule.mode = config.mode
    rule.position = config.position
    rule.scale = config.scale
    if config.transform or (base is not None and base.transform is not None):
        rule.transform = config.transform
    rule.mirror = config.mirror
    rule.bitdepth = config.bitdepth
    rule.vrr = config.vrr
    rule.cm = config.cm
    if not config.enabled:
        rule.disabled = True
    return rule


def _base_rule(config: MonitorConfig, rules: Sequence[MonitorRule]) -> MonitorRule | None:
    index = config.rule_index
    return rules[index] if index is not None and 0 <= index < len(rules) else None


def monitor_rules(configs: Iterable[MonitorConfig], rules: Sequence[MonitorRule]) -> list[MonitorRule]:
    return [config_to_rule(c, _base_rule(c, rules)) for c in configs]


def build_rules(draft: Draft, rules: Sequence[MonitorRule]) -> list[MonitorRule]:
    """The full rule list to write: fallback, then kept rules, then connected monitors (which win)."""
    kept = [rules[i] for i in sorted(set(draft.keep_rules)) if 0 <= i < len(rules)]
    fallbacks = [r for r in kept if r.is_fallback]
    others = [r for r in kept if not r.is_fallback]
    return fallbacks + others + monitor_rules(draft.monitors, rules)


def changed_configs(draft: Draft, monitors: Sequence[MonitorInfo], rules: Sequence[MonitorRule]) -> list[MonitorConfig]:
    """Draft entries that differ from what the file currently says."""
    current = {c.name: c for c in initial_configs(monitors, rules)}
    return [c for c in draft.monitors if c != current.get(c.name)]


def restore_rules(
    outputs_by_monitor: dict[str, set[str]],
    monitors: Sequence[MonitorInfo],
    rules: Sequence[MonitorRule],
    before: dict[str, MonitorInfo] | None = None,
) -> list[MonitorRule]:
    """Rules that put monitors back the way they were before a live preview.

    Each output name used during the preview is re-declared, so preview rules Hyprland
    still holds can no longer take effect. The monitor's file rule supplies fields like
    `icc` or `reserved_area`; mode, position, scale and transform are pinned to what was
    on screen before (`before`), since re-deriving them from Hyprland's implicit defaults
    is not reliable.
    """
    before = before or {}
    restored = []
    for monitor in monitors:
        match = resolve_rule(rules, monitor)
        base = rules[match.index] if match else DEFAULT_RULE
        prior = before.get(monitor.name)
        for output in sorted(outputs_by_monitor.get(monitor.name, ())):
            rule = base.copy()
            rule.output = output
            if prior is not None:
                _pin_to_live(rule, prior)
            restored.append(rule)
    return restored


def _pin_to_live(rule: MonitorRule, monitor: MonitorInfo) -> None:
    if monitor.disabled:
        rule.disabled = True
        return
    rule.disabled = None
    mode = monitor.current_mode
    if mode:
        rule.mode = str(mode)
    rule.position = format_position(monitor.x, monitor.y)
    rule.scale = round(monitor.scale, 6)
    rule.transform = monitor.transform


def live_configs(monitors: Sequence[MonitorInfo], rules: Sequence[MonitorRule]) -> list[MonitorConfig]:
    """Configs capturing the current live layout explicitly (identifiers taken from the file)."""
    by_name = {m.name: m for m in monitors}
    configs = initial_configs(monitors, rules)
    for config in configs:
        monitor = by_name[config.name]
        config.enabled = not monitor.disabled
        if monitor.disabled:
            continue
        mode = monitor.current_mode
        config.mode = str(mode) if mode else "preferred"
        config.position = format_position(monitor.x, monitor.y)
        config.scale = round(monitor.scale, 6)
        config.transform = monitor.transform
        config.mirror = monitor.mirror_of
    return configs


# --- effective geometry --------------------------------------------------------------


def effective_mode(mode: str, monitor: MonitorInfo) -> Mode | None:
    """The mode a config will produce, or None for modelines/unrecognized strings."""
    if mode in SPECIAL_MODES:
        return resolve_special_mode(mode, monitor.available_modes)
    return Mode.parse(mode)


def effective_scale(scale: float | str, monitor: MonitorInfo) -> float:
    if isinstance(scale, (int, float)) and scale > 0:
        return float(scale)
    return monitor.scale if not monitor.disabled and monitor.scale > 0 else 1.0


def _mode_available(mode: Mode, monitor: MonitorInfo) -> bool:
    return any(
        m.width == mode.width and m.height == mode.height and (not mode.refresh or abs(m.refresh - mode.refresh) < 0.05)
        for m in monitor.available_modes
    )


# --- validation ----------------------------------------------------------------------


def validate(draft: Draft, monitors: Sequence[MonitorInfo]) -> ValidationResult:
    by_name = {m.name: m for m in monitors}
    issues: list[Issue] = []
    rects: dict[str, Rect] = {}
    pending_auto: list[tuple[str, int, int]] = []

    def issue(severity: str, code: str, message: str, *names: str) -> None:
        issues.append(Issue(severity, code, message, list(names)))

    for config in draft.monitors:
        monitor = by_name.get(config.name)
        if monitor is None:
            issue("warning", "not-connected", f"{config.name} is no longer connected.", config.name)
            continue
        _check_identifier(config, monitor, monitors, issue)
        if not config.enabled:
            continue
        if config.mirror:
            targets = [m for m in matching_monitors(config.mirror, monitors) if m.name != config.name]
            if not targets:
                issue("error", "bad-mirror", f"{config.name} cannot mirror {config.mirror!r}.", config.name)
            continue

        mode = effective_mode(config.mode, monitor)
        if mode is None:
            issue("info", "custom-mode", f"{config.name} uses a custom mode; its size can't be previewed.", config.name)
            mode = monitor.current_mode
        elif config.mode not in SPECIAL_MODES and not _mode_available(mode, monitor):
            issue("warning", "mode-unavailable", f"{config.name} doesn't advertise {config.mode}; Hyprland will pick the closest mode.", config.name)
        if mode is None:
            continue

        if isinstance(config.scale, float) and not is_valid_scale(mode.width, mode.height, config.scale):
            nearest = nearest_valid_scale(mode.width, mode.height, config.scale)
            hint = f" Try {format_scale(nearest)}." if nearest else ""
            issue("error", "invalid-scale", f"Scale {format_scale(config.scale)} doesn't divide {mode.resolution} evenly.{hint}", config.name)

        width, height = logical_size(mode.width, mode.height, effective_scale(config.scale, monitor), config.transform)
        position = parse_position(config.position)
        if position is None and not monitor.disabled:
            position = (monitor.x, monitor.y)
        if position is None:
            pending_auto.append((config.name, width, height))
        else:
            rects[config.name] = Rect(position[0], position[1], width, height)

    # Monitors that are auto-placed and not currently live go to the right of the rest.
    for name, width, height in pending_auto:
        right = max((r.right for r in rects.values()), default=0)
        top = min((r.y for r in rects.values()), default=0)
        rects[name] = Rect(right, top, width, height)

    for output, count in Counter(c.output for c in draft.monitors if c.output).items():
        if count > 1:
            names = [c.name for c in draft.monitors if c.output == output]
            issue("error", "duplicate-output", f"{' and '.join(names)} use the same identifier {output!r}.", *names)
    for a, b in find_overlaps(rects):
        issue("error", "overlap", f"{a} and {b} overlap.", a, b)
    for name in find_detached(rects):
        issue("warning", "detached", f"{name} doesn't touch any other display; the cursor can't move onto it.", name)
    if draft.monitors and not any(c.enabled for c in draft.monitors if c.name in by_name):
        issue("error", "all-disabled", "At least one display must stay enabled.")

    placements = [Placement(name, r.x, r.y, r.width, r.height) for name, r in rects.items()]
    return ValidationResult(issues, placements)


def _check_identifier(config: MonitorConfig, monitor: MonitorInfo, monitors: Sequence[MonitorInfo], issue) -> None:
    if not config.output.strip():
        issue("error", "empty-output", f"{config.name} needs an identifier.", config.name)
    elif not matches(config.output, monitor):
        issue("error", "output-mismatch", f"{config.output!r} doesn't match {config.name}.", config.name)
    else:
        others = [m.name for m in matching_monitors(config.output, monitors) if m.name != monitor.name]
        if others:
            issue("warning", "output-ambiguous", f"{config.output!r} also matches {', '.join(others)}.", config.name)
