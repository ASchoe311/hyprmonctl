import QtQuick
import HyprMonCtl.Style

Text {
    property bool muted: false

    color: muted ? Theme.textMuted : Theme.text
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontSize
    elide: Text.ElideRight
    verticalAlignment: Text.AlignVCenter
}
