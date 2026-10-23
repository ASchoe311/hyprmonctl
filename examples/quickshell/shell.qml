//@ pragma UseQApplication
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic

// Minimal Quickshell config embedding hyprmonctl. Run it standalone with:
//
//     QML_IMPORT_PATH="$(hyprmonctl qml-path)" qs -p examples/quickshell/shell.qml
//
// In your own shell, copy the LazyLoader + IpcHandler below and bind a key to
// `qs -c <your-config> ipc call displays toggle`.
import QtQuick
import Quickshell
import Quickshell.Io
import HyprMonCtl.Quickshell

ShellRoot {
    LazyLoader {
        id: displays
        active: true  // set to false in a real shell; the IpcHandler opens it on demand

        MonitorConfigWindow {
            visible: true
            onVisibleChanged: if (!visible) displays.active = false
        }
    }

    IpcHandler {
        target: "displays"

        function open(): void { displays.active = true; }
        function close(): void { displays.active = false; }
        function toggle(): void { displays.active = !displays.active; }
    }
}
