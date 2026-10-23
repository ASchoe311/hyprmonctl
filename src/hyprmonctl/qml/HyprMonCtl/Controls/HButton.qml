import QtQuick
import QtQuick.Controls.Basic as T
import HyprMonCtl.Style

// variant: "primary" (accent), "secondary" (tonal) or "text" (flat).
T.Button {
    id: control

    property string variant: "secondary"
    property string iconName

    readonly property color foreground: variant === "primary" ? Theme.accentText : variant === "text" ? Theme.accent : Theme.text

    hoverEnabled: true
    implicitHeight: Theme.controlHeight + 2
    implicitWidth: Math.max(implicitHeight, row.implicitWidth + 32)
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontSize
    font.weight: Font.DemiBold

    background: Rectangle {
        radius: height / 2
        opacity: control.enabled ? 1 : 0.4
        color: control.variant === "primary" ? Theme.accent : control.variant === "secondary" ? Theme.surfaceHighest : "transparent"

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: control.pressed ? Theme.pressed : control.hovered ? Theme.hover : "transparent"
        }
    }

    contentItem: Item {
        implicitWidth: row.implicitWidth
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 8
            opacity: control.enabled ? 1 : 0.6

            Icon {
                visible: control.iconName.length > 0
                anchors.verticalCenter: parent.verticalCenter
                name: control.iconName
                size: 16
                color: control.foreground
            }
            HLabel {
                visible: control.text.length > 0
                anchors.verticalCenter: parent.verticalCenter
                text: control.text
                font: control.font
                color: control.foreground
            }
        }
    }
}
