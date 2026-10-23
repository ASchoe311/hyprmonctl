import QtQuick
import HyprMonCtl.Style

// "−  value  +" control (COSMIC's "Additional scale options").
Row {
    id: root

    property string text
    property bool canDecrease: true
    property bool canIncrease: true
    signal decrease
    signal increase

    spacing: 2

    HIconButton {
        iconName: "minus"
        enabled: root.enabled && root.canDecrease
        onClicked: root.decrease()
    }
    HLabel {
        width: 64
        height: 36
        horizontalAlignment: Text.AlignHCenter
        text: root.text
        muted: !root.enabled
    }
    HIconButton {
        iconName: "plus"
        enabled: root.enabled && root.canIncrease
        onClicked: root.increase()
    }
}
