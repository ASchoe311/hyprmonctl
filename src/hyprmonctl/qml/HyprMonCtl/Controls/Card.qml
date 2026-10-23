import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style

// A rounded surface; children are stacked in a column. `title` adds a muted heading.
Rectangle {
    id: root

    default property alias content: column.data
    property string title
    property alias headerActions: actions.data
    property int padding: Theme.padding
    property int contentSpacing: 0

    color: Theme.surface
    radius: Theme.radius
    implicitHeight: column.implicitHeight + (header.visible ? header.height : 0)

    RowLayout {
        id: header
        visible: root.title.length > 0 || actions.children.length > 0
        anchors { left: parent.left; right: parent.right; top: parent.top }
        anchors.leftMargin: root.padding + 8
        anchors.rightMargin: root.padding
        height: visible ? 48 : 0

        HLabel {
            Layout.fillWidth: true
            text: root.title
            muted: true
        }
        Row {
            id: actions
            spacing: 4
        }
    }

    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: header.visible ? header.bottom : parent.top }
        spacing: root.contentSpacing
    }
}
