import QtQuick
import QtQuick.Controls.Basic as T
import HyprMonCtl.Style

// Purely bound: `checked` follows the model, clicks are handled by the owner
// (so the model stays the single source of truth).
T.AbstractButton {
    id: control

    hoverEnabled: true
    implicitWidth: 52
    implicitHeight: 28

    background: Rectangle {
        radius: height / 2
        color: control.checked ? Theme.accent : Theme.surfaceHighest
        opacity: control.enabled ? 1 : 0.45
        border.width: control.checked ? 0 : 1
        border.color: Theme.tileBorder
        Behavior on color { ColorAnimation { duration: Theme.animationDuration } }
    }

    contentItem: Item {
        Rectangle {
            width: control.checked ? 20 : 16
            height: width
            radius: width / 2
            y: (parent.height - height) / 2
            x: control.checked ? parent.width - width - 4 : 6
            color: control.checked ? Theme.accentText : Theme.tileBorder
            Behavior on x { NumberAnimation { duration: Theme.animationDuration; easing.type: Easing.OutCubic } }
        }
    }
}
