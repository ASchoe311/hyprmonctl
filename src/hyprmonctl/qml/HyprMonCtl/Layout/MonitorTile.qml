import QtQuick
import HyprMonCtl.Style
import HyprMonCtl.Controls
import "Snapping.js" as Snapping
import "Geometry.js" as Geometry

// One display in the arrangement view. Dragging works in layout pixels and only
// commits to the store on release.
Item {
    id: tile

    required property var entry
    required property LayoutCanvas view
    readonly property var rect: view.rectFor(entry.name)
    readonly property bool selected: view.store.selectedName === entry.name

    property bool dragActive: false
    property real dragX: 0
    property real dragY: 0
    readonly property var currentRect: rect ? (dragActive ? { name: entry.name, x: dragX, y: dragY, width: rect.width, height: rect.height } : rect) : null
    readonly property bool overlapping: {
        if (!currentRect)
            return false;
        const others = view.othersOf(entry.name);
        return others.some(o => Geometry.overlaps(currentRect, o));
    }

    visible: rect !== null
    x: rect ? view.offsetX + currentRect.x * view.zoom : 0
    y: rect ? view.offsetY + currentRect.y * view.zoom : 0
    width: rect ? rect.width * view.zoom : 0
    height: rect ? rect.height * view.zoom : 0
    z: dragActive ? 2 : selected ? 1 : 0

    Behavior on x { enabled: !tile.dragActive; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on y { enabled: !tile.dragActive; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: 4
        color: tile.selected ? Theme.accent : Theme.tile
        border.width: 2
        border.color: tile.overlapping ? Theme.error : tile.selected ? Qt.darker(Theme.tileBorder, 1.6) : Theme.tileBorder
        opacity: tile.dragActive ? 0.92 : 1

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: mouse.containsMouse && !tile.selected ? Theme.hover : "transparent"
        }
    }

    Rectangle {
        id: pill
        anchors.centerIn: parent
        anchors.verticalCenterOffset: caption.visible ? -8 : 0
        height: Math.min(36, Math.max(20, tile.height * 0.32))
        width: Math.max(height * 1.6, number.implicitWidth + 28)
        radius: height / 2
        color: Theme.badge

        Text {
            id: number
            anchors.centerIn: parent
            text: tile.entry.id + 1
            color: Theme.badgeText
            font.family: Theme.fontFamily
            font.pixelSize: pill.height * 0.58
            font.weight: Font.Bold
        }
    }

    HLabel {
        id: caption
        anchors { top: pill.bottom; topMargin: 4; horizontalCenter: parent.horizontalCenter }
        width: tile.width - 12
        horizontalAlignment: Text.AlignHCenter
        visible: tile.height > 76 && tile.width > 70
        text: tile.entry.name
        font.pixelSize: Theme.fontSizeSmall
        color: tile.selected ? Theme.accentText : Theme.text
    }

    // Auto-placed displays can move when others change; dragging any display pins them.
    HLabel {
        anchors { top: parent.top; right: parent.right; margins: 8 }
        visible: tile.rect !== null && tile.rect.auto && !tile.dragActive && tile.width > 120 && tile.height > 64
        text: "AUTO"
        font.pixelSize: 10
        font.weight: Font.DemiBold
        font.letterSpacing: 1
        color: tile.selected ? Theme.accentText : Theme.textMuted
    }

    MouseArea {
        id: mouse

        property point pressPoint
        property point origin

        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true  // the page's ScrollView would otherwise take over vertical drags
        cursorShape: tile.dragActive ? Qt.ClosedHandCursor : Qt.OpenHandCursor

        onPressed: event => {
            tile.view.store.select(tile.entry.name);
            pressPoint = mapToItem(tile.view, event.x, event.y);
            origin = Qt.point(tile.rect.x, tile.rect.y);
        }
        onPositionChanged: event => {
            if (!pressed)
                return;
            const p = mapToItem(tile.view, event.x, event.y);
            if (!tile.dragActive && Math.hypot(p.x - pressPoint.x, p.y - pressPoint.y) < 4)
                return;
            if (!tile.dragActive) {
                tile.dragX = origin.x;
                tile.dragY = origin.y;
                tile.dragActive = true;
                tile.view.dragging = true;
            }
            const raw = {
                x: origin.x + (p.x - pressPoint.x) / tile.view.zoom,
                y: origin.y + (p.y - pressPoint.y) / tile.view.zoom,
                width: tile.rect.width,
                height: tile.rect.height
            };
            const snapped = Snapping.snap(raw, tile.view.othersOf(tile.entry.name), tile.view.snapDistance / tile.view.zoom);
            tile.dragX = snapped.x;
            tile.dragY = snapped.y;
            tile.view.guides = snapped.guides;
        }
        onReleased: {
            if (tile.dragActive) {
                const placed = Snapping.attach(tile.currentRect, tile.view.othersOf(tile.entry.name));
                tile.view.store.moveMonitor(tile.entry.name, placed.x, placed.y);
            }
            finish();
        }
        onCanceled: finish()

        function finish() {
            tile.dragActive = false;
            tile.view.guides = [];
            tile.view.dragging = false;
        }
    }
}
