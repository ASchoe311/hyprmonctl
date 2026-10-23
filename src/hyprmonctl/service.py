"""The application service: everything clients can do, independent of transport.

Live previews are reverted by a timer owned here (not by the UI), so a frozen or
blank-screened client still gets its displays back.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from hyprmonctl import API_VERSION, paths
from hyprmonctl.hyprland.ipc import Compositor, HyprlandError
from hyprmonctl.luaconf import discovery
from hyprmonctl.luaconf.parser import ParsedConfig, content_hash, parse_source
from hyprmonctl.luaconf.writer import render_call, render_file, write_atomic
from hyprmonctl.model import draft as drafts
from hyprmonctl.model.identity import candidates, default_identifier, matching_monitors, resolve_rule
from hyprmonctl.model.layout import logical_size
from hyprmonctl.model.monitor import SPECIAL_MODES, MonitorInfo, resolutions, resolve_special_mode
from hyprmonctl.model.rule import KNOWN_FIELDS, LuaRaw, MonitorRule
from hyprmonctl.model.scale import nice_scales, valid_scales
from hyprmonctl.model.state import (
    AppState,
    Draft,
    Issue,
    LiveState,
    MonitorConfig,
    MonitorEntry,
    PreviewInfo,
    ResolutionInfo,
    SavedRule,
    SaveResult,
    ValidationResult,
)
from hyprmonctl.settings import Settings, SettingsStore

Listener = Callable[[str, dict[str, Any]], None]


class ConflictError(RuntimeError):
    """The config file changed on disk since the client loaded it."""


class InvalidDraftError(ValueError):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("; ".join(i.message for i in issues))
        self.issues = issues


class NoPreviewError(RuntimeError):
    """confirm() was called without a pending preview."""


@dataclass
class _LoadedConfig:
    path: Path
    data: bytes | None
    parsed: ParsedConfig

    @property
    def rules(self) -> list[MonitorRule]:
        return self.parsed.rules

    @property
    def hash(self) -> str | None:
        return content_hash(self.data)


@dataclass
class _Preview:
    draft: Draft
    outputs: dict[str, set[str]]  # monitor name -> output names declared during the preview
    before: dict[str, MonitorInfo]  # live state from before the first preview, to restore
    deadline: float
    timeout: int
    timer: threading.Timer


class MonitorService:
    def __init__(
        self,
        compositor: Compositor,
        settings: SettingsStore,
        *,
        timer_factory: Callable[[float, Callable[[], None]], threading.Timer] = threading.Timer,
        clock: Callable[[], float] = time.time,
        main_config: Path | None = None,
    ) -> None:
        self._compositor = compositor
        self._settings = settings
        self._timer_factory = timer_factory
        self._clock = clock
        self._main_config = main_config or paths.hypr_main_config()
        self._lock = threading.RLock()
        self._listeners: list[Listener] = []
        self._preview: _Preview | None = None

    # --- events ----------------------------------------------------------------------

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        for listener in list(self._listeners):
            listener(event, payload)

    def notify_monitors_changed(self, reason: str) -> None:
        self._emit("monitors.changed", {"reason": reason})

    # --- queries ---------------------------------------------------------------------

    @property
    def settings(self) -> Settings:
        return self._settings.load()

    def _load_config(self) -> _LoadedConfig:
        path = self.settings.resolved_lua_path
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return _LoadedConfig(path, None, ParsedConfig())
        return _LoadedConfig(path, data, parse_source(data.decode("utf-8", errors="replace")))

    def state(self) -> AppState:
        with self._lock:
            settings = self.settings
            config = self._load_config()
            monitors = self._compositor.monitors()
            configs = {c.name: c for c in drafts.initial_configs(monitors, config.rules)}
            owners = drafts.owned_rule_indices(monitors, config.rules)
            entries = [
                _monitor_entry(m, monitors, config.rules, configs[m.name]) for m in sorted(monitors, key=lambda m: m.id)
            ]
            return AppState(
                api_version=API_VERSION,
                lua_path=str(config.path),
                lua_path_display=paths.contract(config.path),
                lua_module=discovery.module_name(config.path, self._main_config.parent),
                file_exists=config.data is not None,
                file_hash=config.hash,
                monitors=entries,
                saved_rules=_saved_rules(config.rules, owners, monitors),
                diagnostics=self._diagnostics(config, owners),
                settings=settings,
                preview=PreviewInfo(self._preview.deadline, self._preview.timeout) if self._preview else None,
            )

    def _diagnostics(self, config: _LoadedConfig, owners: dict[int, str]) -> list[Issue]:
        shown = paths.contract(config.path)
        out: list[Issue] = []
        if config.data is None:
            out.append(Issue("info", "file-missing", f"{shown} doesn't exist yet; it will be created when you apply."))
        if config.parsed.error:
            out.append(
                Issue(
                    "error",
                    "parse-error",
                    f"Couldn't read {shown} ({config.parsed.error}). Applying will replace it; a backup is kept.",
                )
            )
        if config.parsed.foreign_lines:
            lines = ", ".join(str(n) for n in config.parsed.foreign_lines)
            out.append(
                Issue(
                    "warning",
                    "foreign-code",
                    f"{shown} contains code other than hl.monitor() calls (line {lines}). "
                    "It will be dropped when you apply; a backup is kept.",
                )
            )
        for index, name in owners.items():
            raw = [f for f in KNOWN_FIELDS if isinstance(getattr(config.rules[index], f), LuaRaw)]
            if raw:
                out.append(
                    Issue(
                        "warning",
                        "raw-values",
                        f"The rule for {name} computes {', '.join(raw)} with Lua expressions; "
                        "applying replaces them with plain values.",
                        [name],
                    )
                )
        required = discovery.is_required(config.path, self._main_config)
        if required is False:
            module = discovery.module_name(config.path, self._main_config.parent)
            fix = f'Add require("{module}") to hyprland.lua' if module else "Move it under ~/.config/hypr and require it"
            out.append(Issue("warning", "not-loaded", f"Hyprland doesn't load {shown}. {fix} so changes persist."))
        try:
            errors = self._compositor.config_errors()
        except HyprlandError:
            errors = []
        if errors:
            out.append(Issue("warning", "hyprland-errors", "Hyprland reports config errors: " + " | ".join(errors)))
        return out

    def validate(self, draft: Draft) -> ValidationResult:
        return drafts.validate(draft, self._compositor.monitors())

    def render(self, draft: Draft) -> str:
        return render_file(drafts.build_rules(draft, self._load_config().rules))

    def render_live(self) -> str:
        """Lua capturing the current live layout, keeping the file's rules for other monitors."""
        config = self._load_config()
        monitors = self._compositor.monitors()
        owners = drafts.owned_rule_indices(monitors, config.rules)
        keep = [i for i in range(len(config.rules)) if i not in owners]
        return render_file(drafts.build_rules(Draft(drafts.live_configs(monitors, config.rules), keep), config.rules))

    def theme(self) -> dict[str, str]:
        """Colors from a matugen-style JSON file (`{"primary": "#rrggbb", ...}`), if configured."""
        source = self.settings.theme_colors_path
        if not source:
            return {}
        try:
            data = json.loads(paths.expand(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, str) and v.startswith("#")}

    # --- actions ---------------------------------------------------------------------

    def update_settings(self, patch: dict[str, Any]) -> Settings:
        settings = self._settings.update(patch)
        self._emit("settings.changed", {})
        return settings

    def preview(self, draft: Draft) -> PreviewInfo:
        """Apply a draft live; it reverts after `confirmTimeout` seconds unless confirmed."""
        with self._lock:
            settings = self.settings
            config = self._load_config()
            self._check_hash(draft, config)
            monitors = self._compositor.monitors()
            errors = drafts.validate(draft, monitors).errors
            if errors:
                raise InvalidDraftError(errors)

            outputs = self._preview.outputs if self._preview else {}
            before = self._preview.before if self._preview else {m.name: m for m in monitors}
            if self._preview:
                self._preview.timer.cancel()
            # Re-apply monitors touched by an earlier, still-pending preview even if they now
            # match the file again; otherwise they would keep the earlier preview's settings.
            changed = drafts.changed_configs(draft, monitors, config.rules)
            targets = [c for c in draft.monitors if c in changed or c.name in outputs]
            for c in targets:
                outputs.setdefault(c.name, set()).add(c.output)
            try:
                self._eval(drafts.monitor_rules(targets, config.rules))
            except HyprlandError:
                self._restore(outputs, before)
                self._preview = None
                raise

            timeout = settings.confirm_timeout
            timer = self._timer_factory(timeout, self._on_timeout)
            timer.daemon = True
            self._preview = _Preview(draft, outputs, before, self._clock() + timeout, timeout, timer)
            timer.start()
            info = PreviewInfo(self._preview.deadline, timeout)
        self._emit("preview.started", {"deadline": info.deadline, "timeout": timeout})
        return info

    def confirm(self) -> SaveResult:
        with self._lock:
            if self._preview is None:
                raise NoPreviewError("there is no pending preview to keep")
            return self.save(self._preview.draft)

    def revert(self) -> bool:
        with self._lock:
            if self._preview is None:
                return False
            self._end_preview(reason="user")
            return True

    def save(self, draft: Draft) -> SaveResult:
        with self._lock:
            settings = self.settings
            config = self._load_config()
            self._check_hash(draft, config)
            text = render_file(drafts.build_rules(draft, config.rules))
            backup = write_atomic(config.path, text, backup=settings.backup)
            if self._preview:
                self._preview.timer.cancel()
                self._preview = None
            errors: list[str] = []
            # Reloading when Hyprland doesn't load this file would discard the applied layout.
            if settings.reload_after_save and discovery.is_required(config.path, self._main_config) is not False:
                self._compositor.reload()
                errors = self._compositor.config_errors()
            result = SaveResult(
                path=str(config.path),
                backup_path=str(backup) if backup else None,
                file_hash=content_hash(text.encode("utf-8")),
                config_errors=errors,
            )
        self._emit("config.saved", {"path": result.path})
        return result

    def close(self) -> None:
        """Revert any unconfirmed preview (the client went away)."""
        with self._lock:
            if self._preview:
                self._end_preview(reason="closed")

    # --- internals -------------------------------------------------------------------

    def _check_hash(self, draft: Draft, config: _LoadedConfig) -> None:
        if draft.file_hash is not None and draft.file_hash != config.hash:
            raise ConflictError(f"{paths.contract(config.path)} changed on disk; reload before applying")

    def _eval(self, rules: list[MonitorRule]) -> None:
        if rules:
            self._compositor.eval("\n".join(render_call(rule) for rule in rules))

    def _restore(self, outputs: dict[str, set[str]], before: dict[str, MonitorInfo]) -> None:
        monitors = self._compositor.monitors()
        self._eval(drafts.restore_rules(outputs, monitors, self._load_config().rules, before))

    def _on_timeout(self) -> None:
        with self._lock:
            if self._preview is None or self._clock() < self._preview.deadline - 0.5:
                return
            self._end_preview(reason="timeout")

    def _end_preview(self, reason: str) -> None:
        preview, self._preview = self._preview, None
        preview.timer.cancel()
        error = None
        try:
            self._restore(preview.outputs, preview.before)
        except HyprlandError as exc:
            error = str(exc)
        self._emit("preview.reverted", {"reason": reason, "error": error})


# --- state assembly ----------------------------------------------------------------------


def _monitor_entry(
    monitor: MonitorInfo, monitors: list[MonitorInfo], rules: list[MonitorRule], config: MonitorConfig
) -> MonitorEntry:
    match = resolve_rule(rules, monitor)
    logical = logical_size(monitor.width, monitor.height, monitor.scale, monitor.transform)
    special = {name: str(m) for name in SPECIAL_MODES if (m := resolve_special_mode(name, monitor.available_modes))}
    return MonitorEntry(
        id=monitor.id,
        name=monitor.name,
        description=monitor.description,
        make=monitor.make,
        model=monitor.model,
        serial=monitor.serial,
        label=monitor.label,
        internal=monitor.is_internal,
        focused=monitor.focused,
        diagonal_inches=round(monitor.diagonal_inches, 1) if monitor.diagonal_inches else None,
        live=LiveState(
            x=monitor.x,
            y=monitor.y,
            width=monitor.width,
            height=monitor.height,
            refresh_rate=round(monitor.refresh_rate, 2),
            scale=monitor.scale,
            transform=monitor.transform,
            disabled=monitor.disabled,
            mirror_of=monitor.mirror_of,
            vrr=monitor.vrr,
            bitdepth=monitor.bitdepth,
            color_preset=monitor.color_preset,
            logical_width=logical[0],
            logical_height=logical[1],
        ),
        resolutions=[
            ResolutionInfo(w, h, rates, valid_scales(w, h), nice_scales(w, h))
            for w, h, rates in resolutions(monitor.available_modes)
        ],
        special_modes=special,
        identifiers=candidates(monitor, monitors),
        default_identifier=default_identifier(monitor, monitors),
        matched_by_fallback=bool(match and match.fallback),
        config=config,
    )


def _saved_rules(rules: list[MonitorRule], owners: dict[int, str], monitors: list[MonitorInfo]) -> list[SavedRule]:
    saved = []
    for index, rule in enumerate(rules):
        if index in owners:
            continue
        if rule.is_fallback:
            status = "fallback"
        elif matching_monitors(rule.output_name, monitors):
            status = "overridden"
        else:
            status = "disconnected"
        saved.append(
            SavedRule(
                index=index,
                output=rule.output_name,
                status=status,
                mode=_text(rule.mode),
                position=_text(rule.position),
                scale=_text(rule.scale),
                disabled=rule.is_disabled,
                lua=render_call(rule),
            )
        )
    return saved


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, LuaRaw):
        return value.source
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
