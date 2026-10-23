pragma ComponentBehavior: Bound
import QtQuick
import HyprMonCtl.Style

// Tabs with an accent underline. They share the width equally when they fit; otherwise
// they keep their natural width and scroll horizontally, keeping the current tab in view.
// `tabs`: array of { key, text, badge?, dim? }.
Item {
    id: root

    property var tabs: []
    property var currentKey
    signal selected(var key)

    readonly property real naturalWidth: {
        let total = 0;
        for (let i = 0; i < repeater.count; ++i) {
            const tab = repeater.itemAt(i) as TabButton;
            if (tab)
                total += tab.naturalWidth;
        }
        return total;
    }
    readonly property bool overflowing: naturalWidth > width

    implicitHeight: 52

    function scrollTo(x) {
        scroll.to = Math.max(0, Math.min(x, flick.contentWidth - flick.width));
        scroll.restart();
    }

    function ensureCurrentVisible() {
        if (!overflowing)
            return;
        for (let i = 0; i < repeater.count; ++i) {
            const tab = repeater.itemAt(i) as TabButton;
            if (!tab || tab.modelData.key !== currentKey)
                continue;
            if (tab.x < flick.contentX)
                scrollTo(tab.x - 32);
            else if (tab.x + tab.width > flick.contentX + flick.width)
                scrollTo(tab.x + tab.width - flick.width + 32);
            return;
        }
    }

    onCurrentKeyChanged: Qt.callLater(ensureCurrentVisible)
    onOverflowingChanged: Qt.callLater(ensureCurrentVisible)

    component TabButton: Item {
        id: tab

        required property var modelData
        readonly property bool active: modelData.key === root.currentKey
        readonly property real badgeSpace: badge.visible ? badge.width + content.spacing : 0
        readonly property real naturalWidth: label.implicitWidth + badgeSpace + 40

        width: root.overflowing ? naturalWidth : root.width / Math.max(1, repeater.count)
        height: row.height

        Rectangle {
            anchors.fill: parent
            anchors.bottomMargin: 2
            topLeftRadius: Theme.radius
            topRightRadius: Theme.radius
            color: tab.active ? Theme.surface : mouse.containsMouse ? Theme.hover : "transparent"
        }

        Row {
            id: content
            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                id: badge
                visible: tab.modelData.badge !== undefined
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(height, badgeText.implicitWidth + 12)
                height: 20
                radius: height / 2
                color: tab.active ? Theme.accent : Theme.badge
                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: tab.modelData.badge !== undefined ? tab.modelData.badge : ""
                    color: tab.active ? Theme.accentText : Theme.badgeText
                    font.family: Theme.fontFamily
                    font.pixelSize: 12
                    font.weight: Font.Bold
                }
            }
            HLabel {
                id: label
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, tab.width - 40 - tab.badgeSpace)
                text: tab.modelData.text
                color: tab.active ? Theme.accent : Theme.text
                opacity: tab.modelData.dim && !tab.active ? 0.6 : 1
                font.weight: tab.active ? Font.DemiBold : Font.Normal
            }
        }

        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 4
            color: Theme.accent
            visible: tab.active
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.selected(tab.modelData.key)
        }
    }

    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 2
        color: Theme.accent
        opacity: 0.55
    }

    Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: row.width
        flickableDirection: Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds
        interactive: root.overflowing
        clip: true

        Row {
            id: row
            height: flick.height

            Repeater {
                id: repeater
                model: root.tabs
                delegate: TabButton {}
            }
        }
    }

    NumberAnimation {
        id: scroll
        target: flick
        property: "contentX"
        duration: 200
        easing.type: Easing.OutCubic
    }

    // A plain mouse wheel scrolls the tabs sideways, but only when they overflow, so the
    // page keeps scrolling normally otherwise.
    WheelHandler {
        enabled: root.overflowing
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: event => {
            const delta = event.angleDelta.x !== 0 ? event.angleDelta.x : event.angleDelta.y;
            scroll.stop();
            flick.contentX = Math.max(0, Math.min(flick.contentX - delta, flick.contentWidth - flick.width));
        }
    }

    // Edge fades hint that more tabs are hidden in that direction.
    Rectangle {
        visible: root.overflowing && flick.contentX > 1
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; bottomMargin: 4 }
        width: 32
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.background }
            GradientStop { position: 1; color: "transparent" }
        }
    }
    Rectangle {
        visible: root.overflowing && flick.contentX < flick.contentWidth - flick.width - 1
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom; bottomMargin: 4 }
        width: 32
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 1; color: Theme.background }
        }
    }
}
