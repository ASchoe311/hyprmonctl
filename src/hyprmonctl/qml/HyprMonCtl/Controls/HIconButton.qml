import QtQuick
import QtQuick.Controls.Basic as T
import HyprMonCtl.Style

T.AbstractButton {
    id: control

    property string iconName
    property color iconColor: Theme.text
    property string tooltip

    hoverEnabled: true
    implicitWidth: 36
    implicitHeight: 36

    T.ToolTip.visible: hovered && tooltip.length > 0
    T.ToolTip.delay: 500
    T.ToolTip.text: tooltip

    background: Rectangle {
        radius: width / 2
        color: control.pressed ? Theme.pressed : control.hovered ? Theme.hover : "transparent"
    }
    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            color: control.iconColor
            opacity: control.enabled ? 1 : 0.4
        }
    }
}
