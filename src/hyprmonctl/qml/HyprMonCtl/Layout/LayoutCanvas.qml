pragma ComponentBehavior: Bound
import QtQuick
import HyprMonCtl.Style
import "Geometry.js" as Geometry

// Zoom-to-fit view of the monitor layout. The view transform is frozen while a tile
// is dragged so the scene doesn't shift under the cursor, then animates to the new fit.
Item {
    id: canvas

    required property var store
    property int snapDistance: 16
    property int margin: 28

    property bool dragging: false
    property var guides: []
    property real zoom: 0.1
    property real offsetX: 0
    property real offsetY: 0

    readonly property var rects: Geometry.layoutRects(store.monitors, store.configs)

    function rectFor(name) {
        for (const r of rects)
            if (r.name === name)
                return r;
        return null;
    }

    function othersOf(name) {
        return rects.filter(r => r.name !== name);
    }

    function refit() {
        if (dragging || width <= 0 || height <= 0)
            return;
        const b = Geometry.bounds(rects);
        const fit = Math.min((width - 2 * margin) / b.width, (height - 2 * margin) / b.height);
        // Use the local value: reading `zoom` back would give the in-flight animated value.
        const z = fit > 0 ? fit : 0.1;
        zoom = z;
        offsetX = (width - b.width * z) / 2 - b.x * z;
        offsetY = (height - b.height * z) / 2 - b.y * z;
    }

    onRectsChanged: refit()
    onWidthChanged: refit()
    onHeightChanged: refit()
    onDraggingChanged: refit()

    Behavior on zoom { enabled: !canvas.dragging; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on offsetX { enabled: !canvas.dragging; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on offsetY { enabled: !canvas.dragging; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

    Repeater {
        model: canvas.store.monitors

        delegate: MonitorTile {
            required property var modelData
            entry: modelData
            view: canvas
        }
    }

    Repeater {
        model: canvas.guides

        delegate: Rectangle {
            id: guide
            required property var modelData
            readonly property bool vertical: modelData.axis === "x"
            x: vertical ? canvas.offsetX + guide.modelData.at * canvas.zoom : 0
            y: vertical ? 0 : canvas.offsetY + guide.modelData.at * canvas.zoom
            width: vertical ? 1 : canvas.width
            height: vertical ? canvas.height : 1
            color: Theme.accent
            opacity: 0.7
            z: 3
        }
    }
}
