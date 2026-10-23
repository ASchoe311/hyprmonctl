# gui/: standalone PySide6 host

Imported only for `hyprmonctl gui`. PySide6 is the optional `gui` extra, and
`app.run` prints an install hint if it's missing.

| File | Role |
|---|---|
| `app.py` | Sets the `Basic` Controls style and Qt logging filters, creates `QGuiApplication` (`setDesktopFileName(APP_ID)` sets the Wayland app id `hyprmonctl`), builds the service, injects `InProcessTransport` into `qml/Main.qml` as a required initial property, and adds `paths.qml_dir()` to the import path. SIGINT quits; on exit, `transport.close()` reverts any pending preview. |
| `transport.py` | `InProcessTransport(QObject)`: `send(line)` slot, `messageReceived(line)` signal (named argument `line`, which QML handlers rely on). Requests run on a single-thread executor, so they stay ordered and never block the UI. Signals emitted from worker threads are queued to the GUI thread automatically. |

## Notes

- **Silenced log categories** (`QT_LOGGING_RULES` still overrides):
  - `qt.qpa.wayland.textinput`: Qt noise when a field loses focus while the window is
    unfocused.
  - `qt.qpa.services`: the portal rejects the app id until
    `hyprmonctl install-desktop` has run.
- **Python versions:** the venv uses Python 3.12 (PySide6 wheels); the core stays 3.11+
  compatible.
- **Screenshot without a window:** use `tools/render_ui.py` (offscreen platform, same
  wiring as `app.py`). See the `hyprmonctl-verify` skill.
