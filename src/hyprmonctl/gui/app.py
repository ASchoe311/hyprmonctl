"""Standalone GUI host: a PySide6 window running the shared QML module."""

from __future__ import annotations

import os
import signal
import sys

from hyprmonctl import paths


def run(lua_path: str | None = None) -> int:
    try:
        from PySide6.QtCore import QLoggingCategory, QTimer
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        print(
            "hyprmonctl: the GUI needs PySide6. Install with the gui extra, e.g. `uv tool install 'hyprmonctl[gui]'`.",
            file=sys.stderr,
        )
        return 1

    from hyprmonctl.cli import build_service
    from hyprmonctl.desktop import APP_ID
    from hyprmonctl.gui.transport import InProcessTransport

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    # Harmless Qt noise (QT_LOGGING_RULES still overrides this when debugging):
    # - text-input-v3 complains when a field loses focus while the window is unfocused;
    # - the portal rejects our app id until `hyprmonctl install-desktop` has been run.
    QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput.warning=false\nqt.qpa.services.warning=false")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("hyprmonctl")
    app.setApplicationDisplayName("Displays")
    app.setDesktopFileName(APP_ID)  # Wayland app_id, for window rules and the portal

    service, ipc = build_service(lua_path)
    transport = InProcessTransport(service, ipc)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(paths.qml_dir()))
    engine.setInitialProperties({"transport": transport})
    engine.load(str(paths.qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        transport.close()
        return 1

    # Let Ctrl+C in a terminal quit cleanly (Python only sees signals between Qt events).
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    heartbeat = QTimer()
    heartbeat.start(250)
    heartbeat.timeout.connect(lambda: None)

    code = app.exec()
    transport.close()  # reverts an unconfirmed preview
    return code
