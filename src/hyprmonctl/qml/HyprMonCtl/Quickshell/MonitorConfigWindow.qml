import QtQuick
import Quickshell
import HyprMonCtl
import HyprMonCtl.Style

// Drop-in floating window for Quickshell configs:
//
//     import HyprMonCtl.Quickshell
//     MonitorConfigWindow { visible: true }
//
// The backend process only runs while the window is visible.
FloatingWindow {
    id: window

    property list<string> command: ["hyprmonctl", "serve"]
    property alias configurator: configurator

    implicitWidth: 900
    implicitHeight: 900
    title: "Displays"
    color: Theme.background

    ProcessTransport {
        id: transport
        command: window.command
        running: window.visible
    }

    MonitorConfigurator {
        id: configurator
        anchors.fill: parent
        transport: transport.connected ? transport : null
    }
}
