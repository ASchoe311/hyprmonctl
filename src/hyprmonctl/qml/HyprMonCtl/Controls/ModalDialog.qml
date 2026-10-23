import QtQuick
import QtQuick.Controls.Basic as T
import QtQuick.Layouts
import HyprMonCtl.Style

// An in-scene modal (no Popup/Overlay needed, so it works in any host window).
// Place it as a full-size child of the page; set `open` to show it. The title and
// buttons stay visible; the body scrolls when the window is too short for it.
Item {
    id: root

    default property alias content: body.data
    property alias buttons: buttonRow.data
    property string title
    property bool open: false
    property bool dismissable: true
    property int dialogWidth: 520
    signal dismissed

    anchors.fill: parent
    visible: opacity > 0
    opacity: open ? 1 : 0
    z: 100
    Behavior on opacity { NumberAnimation { duration: Theme.animationDuration } }

    function close() {
        open = false;
        dismissed();
    }

    Keys.onEscapePressed: if (dismissable) close()
    onOpenChanged: if (open) forceActiveFocus()

    Rectangle {
        anchors.fill: parent
        color: Theme.scrim
        MouseArea {
            anchors.fill: parent
            onClicked: if (root.dismissable) root.close()
        }
    }

    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: Math.min(root.dialogWidth, root.width - 32)
        height: Math.min(layout.implicitHeight + 2 * Theme.padding, root.height - 32)
        radius: Theme.radius + 4
        color: Theme.surface
        border.color: Theme.divider
        scale: root.open ? 1 : 0.96
        Behavior on scale { NumberAnimation { duration: Theme.animationDuration; easing.type: Easing.OutCubic } }

        MouseArea { anchors.fill: parent }  // swallow clicks so they don't dismiss

        ColumnLayout {
            id: layout
            anchors.fill: parent
            anchors.margins: Theme.padding
            spacing: Theme.spacing

            HLabel {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                font.pixelSize: Theme.fontSizeLarge + 2
                font.weight: Font.DemiBold
            }
            T.ScrollView {
                id: scroller
                readonly property bool overflowing: contentHeight > height + 1

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: body.implicitHeight
                contentWidth: availableWidth
                contentHeight: body.implicitHeight
                clip: true

                ColumnLayout {
                    id: body
                    width: scroller.availableWidth - (scroller.overflowing ? 14 : 0)
                    spacing: Theme.spacing
                }
            }
            RowLayout {
                id: buttonRow
                Layout.alignment: Qt.AlignRight
                spacing: 8
            }
        }
    }
}
