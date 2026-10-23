import QtQuick
import HyprMonCtl.Style

// Transient message at the bottom of its parent. Call show(text, kind).
Rectangle {
    id: root

    property string kind: "info"  // "info" | "error" | "success"

    function show(message, messageKind) {
        label.text = message;
        kind = messageKind || "info";
        hideTimer.interval = kind === "error" ? 7000 : 3500;
        hideTimer.restart();
        shown = true;
    }

    property bool shown: false

    anchors.horizontalCenter: parent.horizontalCenter
    y: shown ? parent.height - height - 24 : parent.height + 8
    width: Math.min(row.implicitWidth + 32, parent.width - 48)
    height: Math.max(44, label.implicitHeight + 20)
    radius: height / 2
    color: Theme.surfaceHighest
    border.color: kind === "error" ? Theme.error : Theme.divider
    z: 200
    visible: y < parent.height
    Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

    Timer {
        id: hideTimer
        onTriggered: root.shown = false
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 10
        width: Math.min(implicitWidth, root.width - 32)

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            name: root.kind === "error" ? "alert" : root.kind === "success" ? "check" : "info"
            color: root.kind === "error" ? Theme.error : Theme.accent
        }
        HLabel {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, root.parent ? root.parent.width - 120 : 400)
            wrapMode: Text.Wrap
            elide: Text.ElideNone
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.shown = false
    }
}
