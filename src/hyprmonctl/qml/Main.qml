import QtQuick
import QtQuick.Controls.Basic
import HyprMonCtl
import HyprMonCtl.Style

// Standalone window used by `hyprmonctl gui`; the transport is injected by gui/app.py.
ApplicationWindow {
    id: window

    required property var transport

    width: 900
    height: 900
    minimumWidth: 600
    minimumHeight: 520
    visible: true
    title: "Displays"
    color: Theme.background

    MonitorConfigurator {
        objectName: "configurator"
        anchors.fill: parent
        transport: window.transport
    }
}
