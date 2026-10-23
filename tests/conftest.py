from __future__ import annotations

import json
from pathlib import Path

import pytest

from hyprmonctl.model.monitor import MonitorInfo
from hyprmonctl.service import MonitorService
from hyprmonctl.settings import SettingsStore

FIXTURES = Path(__file__).parent / "fixtures"


def load_monitors() -> list[MonitorInfo]:
    """Captured `hyprctl monitors all -j`: eDP-1 (laptop, no serial) + DP-1 (Dell P2725QE)."""
    return [MonitorInfo.from_hyprctl(m) for m in json.loads((FIXTURES / "monitors.json").read_text())]


class FakeCompositor:
    def __init__(self, monitors: list[MonitorInfo]) -> None:
        self._monitors = monitors
        self.evals: list[str] = []
        self.reloads = 0
        self.fail_eval = False

    def monitors(self) -> list[MonitorInfo]:
        return self._monitors

    def eval(self, code: str) -> None:
        from hyprmonctl.hyprland.ipc import HyprlandError

        if self.fail_eval:
            raise HyprlandError("boom")
        self.evals.append(code)

    def reload(self) -> None:
        self.reloads += 1

    def config_errors(self) -> list[str]:
        return []


class FakeTimer:
    def __init__(self, interval: float, function) -> None:
        self.interval = interval
        self.function = function
        self.started = False
        self.cancelled = False
        self.daemon = False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        self.function()


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def monitors() -> list[MonitorInfo]:
    return load_monitors()


@pytest.fixture
def user_lua() -> str:
    return (FIXTURES / "user_monitors.lua").read_text()


@pytest.fixture
def env(tmp_path, monitors, user_lua):
    """A service wired to fakes, with the user's real monitors.lua copied into tmp_path."""
    lua_path = tmp_path / "hypr" / "config" / "monitors.lua"
    lua_path.parent.mkdir(parents=True)
    lua_path.write_text(user_lua)
    main_config = tmp_path / "hypr" / "hyprland.lua"
    main_config.write_text('require("config.monitors")\n')

    compositor = FakeCompositor(monitors)
    timers: list[FakeTimer] = []

    def timer_factory(interval, function):
        timer = FakeTimer(interval, function)
        timers.append(timer)
        return timer

    clock = FakeClock()
    store = SettingsStore(tmp_path / "settings.json", overrides={"luaPath": str(lua_path), "themeColorsPath": ""})
    service = MonitorService(compositor, store, timer_factory=timer_factory, clock=clock, main_config=main_config)
    events: list[tuple[str, dict]] = []
    service.subscribe(lambda event, payload: events.append((event, payload)))

    class Env:
        pass

    e = Env()
    e.service, e.compositor, e.timers, e.clock, e.events = service, compositor, timers, clock, events
    e.lua_path, e.main_config, e.tmp_path = lua_path, main_config, tmp_path
    return e
