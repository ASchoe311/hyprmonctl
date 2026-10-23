#!/usr/bin/env python3
"""Render the hyprmonctl UI offscreen to a PNG; no window appears on screen.

Run it with the project venv (needs the `gui` extra):

    .venv/bin/python tools/render_ui.py out.png --size 900x1200 --lua-path /tmp/scratch.lua \\
        --js "store.select('DP-1')" --drag 578,318,120,360 --js "cfg.showLua()"

Steps run in the order given. `--js` runs with `cfg` (the MonitorConfigurator),
`store` (its MonitorStore) and `win` in scope; use console.log("...") to print
values. `--drag` and `--wheel` send real mouse events in window coordinates.

The tool reads live monitor state from Hyprland. It only changes the live layout if
your JS calls store.apply()/store.keep(), and only writes a file if you call
store.keep() or store.saveWithoutPreview(). Pass --lua-path pointing at a scratch
copy whenever a step might save.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QWheelEvent  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401  (lets rootObjects() return a QQuickWindow)
from PySide6.QtTest import QTest  # noqa: E402

from hyprmonctl import paths  # noqa: E402
from hyprmonctl.cli import build_service  # noqa: E402
from hyprmonctl.gui.transport import InProcessTransport  # noqa: E402


class _Step(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        namespace.steps.append((self.dest, values))


def pump(seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)
        time.sleep(0.01)


def ints(text: str, count: int) -> list[int]:
    values = [int(v) for v in text.split(",")]
    if len(values) != count:
        raise SystemExit(f"expected {count} comma-separated integers, got {text!r}")
    return values


def drag(win, spec: str) -> None:
    x1, y1, x2, y2 = ints(spec, 4)
    QTest.mousePress(win, Qt.LeftButton, Qt.NoModifier, QPoint(x1, y1))
    for i in range(1, 21):
        QTest.mouseMove(win, QPoint(x1 + (x2 - x1) * i // 20, y1 + (y2 - y1) * i // 20))
        pump(0.02)
    QTest.mouseRelease(win, Qt.LeftButton, Qt.NoModifier, QPoint(x2, y2))


def wheel(win, spec: str) -> None:
    x, y, dy = ints(spec, 3)
    pos = QPointF(x, y)
    for _ in range(max(1, abs(dy) // 120)):
        step = QPoint(0, 120 if dy > 0 else -120)
        event = QWheelEvent(pos, pos, QPoint(0, 0), step, Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QGuiApplication.sendEvent(win, event)
        pump(0.05)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", help="PNG to write")
    parser.add_argument("--size", default="900x1000", help="window size WIDTHxHEIGHT (logical px)")
    parser.add_argument("--lua-path", help="config file to load (defaults to the hyprmonctl setting)")
    parser.add_argument("--js", dest="js", action=_Step, help="JavaScript to evaluate (repeatable)")
    parser.add_argument("--drag", dest="drag", action=_Step, help="mouse drag x1,y1,x2,y2 (repeatable)")
    parser.add_argument("--wheel", dest="wheel", action=_Step, help="mouse wheel x,y,deltaY (+up/-down)")
    parser.add_argument("--wait", dest="wait", action=_Step, type=float, help="extra seconds to wait")
    parser.set_defaults(steps=[])
    args = parser.parse_args()
    width, height = (int(v) for v in args.size.lower().split("x"))

    app = QGuiApplication(sys.argv[:1])
    service, _ipc = build_service(args.lua_path)
    transport = InProcessTransport(service, None)
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(paths.qml_dir()))
    engine.setInitialProperties({"transport": transport})
    engine.load(str(paths.qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        return 1
    win = engine.rootObjects()[0]
    win.setProperty("width", width)
    win.setProperty("height", height)
    pump(1.5)  # initial state.get + theme + validation

    cfg = win.findChild(QObject, "configurator")
    scope = engine.globalObject()
    scope.setProperty("cfg", engine.newQObject(cfg))
    scope.setProperty("win", engine.newQObject(win))
    for kind, value in args.steps:
        if kind == "js":
            result = engine.evaluate(f"(function () {{ var store = cfg.store; {value}\n}})()")
            if result.isError():
                print("JS error:", result.toString(), file=sys.stderr)
        elif kind == "drag":
            drag(win, value)
        elif kind == "wheel":
            wheel(win, value)
        elif kind == "wait":
            pump(value)
        pump(0.6)

    win.grabWindow().save(args.output)
    print(f"saved {args.output}")
    transport.close()  # reverts a preview a step may have started
    return 0


if __name__ == "__main__":
    sys.exit(main())
