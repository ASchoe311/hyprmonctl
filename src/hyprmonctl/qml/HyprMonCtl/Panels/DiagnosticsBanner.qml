pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls

// Problems with the config file itself (unreadable, extra code, not loaded by Hyprland).
Rectangle {
    id: banner

    required property var diagnostics
    readonly property string worst: diagnostics.some(d => d.severity === "error") ? "error" : diagnostics.some(d => d.severity === "warning") ? "warning" : "info"

    Layout.fillWidth: true
    visible: diagnostics.length > 0
    implicitHeight: column.implicitHeight + 24
    radius: Theme.radius
    color: Qt.rgba(Theme.severityColor(worst).r, Theme.severityColor(worst).g, Theme.severityColor(worst).b, 0.10)
    border.color: Qt.rgba(Theme.severityColor(worst).r, Theme.severityColor(worst).g, Theme.severityColor(worst).b, 0.45)

    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 16 }
        spacing: 8

        Repeater {
            model: banner.diagnostics

            delegate: RowLayout {
                id: diagnostic
                required property var modelData
                Layout.fillWidth: true
                spacing: 10

                Icon {
                    Layout.alignment: Qt.AlignTop
                    name: diagnostic.modelData.severity === "info" ? "info" : "alert"
                    color: Theme.severityColor(diagnostic.modelData.severity === "info" ? "warning" : diagnostic.modelData.severity)
                }
                HLabel {
                    Layout.fillWidth: true
                    text: diagnostic.modelData.message
                    wrapMode: Text.Wrap
                    elide: Text.ElideNone
                }
            }
        }
    }
}
