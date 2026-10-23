import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style

// One "label ... control" line of a settings card, COSMIC style.
Item {
    id: root

    default property alias control: controlSlot.data
    property string label
    property string caption
    property color captionColor: Theme.textMuted
    property bool showDivider: true
    property int horizontalPadding: Theme.padding + 8
    property bool clickable: false
    signal clicked

    Layout.fillWidth: true
    implicitHeight: Math.max(Theme.rowHeight, layout.implicitHeight + 20)

    Rectangle {
        visible: root.showDivider
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1
        color: Theme.divider
    }

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        enabled: root.clickable
        hoverEnabled: root.clickable
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 1
            color: rowMouse.containsMouse ? Theme.hover : "transparent"
        }
    }

    RowLayout {
        id: layout
        anchors.fill: parent
        anchors.leftMargin: root.horizontalPadding
        anchors.rightMargin: root.horizontalPadding - 6
        spacing: Theme.spacing

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 2

            HLabel {
                Layout.fillWidth: true
                text: root.label
            }
            HLabel {
                Layout.fillWidth: true
                visible: root.caption.length > 0
                text: root.caption
                color: root.captionColor
                font.pixelSize: Theme.fontSizeSmall
                wrapMode: Text.Wrap
                elide: Text.ElideNone
            }
        }

        Row {
            id: controlSlot
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            spacing: 8
        }
    }
}
