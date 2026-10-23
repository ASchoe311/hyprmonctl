import QtQuick
import QtQuick.Controls.Basic as T
import HyprMonCtl.Style

T.TextField {
    id: control

    property bool invalid: false
    property bool monospace: false

    implicitHeight: Theme.controlHeight
    implicitWidth: 120
    leftPadding: 10
    rightPadding: 10
    color: Theme.text
    placeholderTextColor: Theme.textMuted
    selectionColor: Theme.accent
    selectedTextColor: Theme.accentText
    font.family: monospace ? Theme.monoFamily : Theme.fontFamily
    font.pixelSize: Theme.fontSize
    verticalAlignment: TextInput.AlignVCenter
    selectByMouse: true

    background: Rectangle {
        radius: Theme.radiusSmall
        color: Theme.surfaceHigh
        border.width: control.activeFocus || control.invalid ? 2 : 1
        border.color: control.invalid ? Theme.error : control.activeFocus ? Theme.accent : Theme.divider
    }
}
