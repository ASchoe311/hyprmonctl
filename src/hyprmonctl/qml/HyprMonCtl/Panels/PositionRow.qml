import QtQuick
import HyprMonCtl.Style
import HyprMonCtl.Controls
import HyprMonCtl.Layout
import "Format.js" as Format

// Manual x/y (kept in sync with the canvas) or one of Hyprland's auto placements.
SettingsRow {
    id: row

    required property var store
    required property string name
    readonly property var config: store.config(name)
    readonly property var explicit: config ? Geometry.parsePosition(config.position) : null
    readonly property var shown: Geometry.layoutRects(store.monitors, store.configs).find(r => r.name === name) || null

    label: "Position"
    caption: !explicit && shown ? "Currently at " + shown.x + ", " + shown.y + " in the layout" : "Top-left corner, in logical pixels"

    HComboBox {
        anchors.verticalCenter: parent.verticalCenter
        value: row.explicit ? "manual" : row.config ? row.config.position : "auto"
        options: [{ text: "Manual", value: "manual" }].concat(Format.autoPositions)
        onPicked: value => {
            if (value !== "manual")
                row.store.setField(row.name, "position", value);
            else if (row.shown)
                row.store.moveMonitor(row.name, row.shown.x, row.shown.y);
        }
    }

    component Coordinate: HTextField {
        id: coord
        property int value
        signal committed(int value)
        width: 84
        horizontalAlignment: TextInput.AlignRight
        validator: IntValidator { bottom: -100000; top: 100000 }
        text: value
        onValueChanged: if (!activeFocus) text = value
        onEditingFinished: if (acceptableInput && parseInt(text) !== value) committed(parseInt(text))
    }

    HLabel {
        visible: row.explicit !== null
        anchors.verticalCenter: parent.verticalCenter
        text: "X"
        muted: true
    }
    Coordinate {
        visible: row.explicit !== null
        value: row.explicit ? row.explicit.x : 0
        onCommitted: v => row.store.moveMonitor(row.name, v, row.explicit.y)
    }
    HLabel {
        visible: row.explicit !== null
        anchors.verticalCenter: parent.verticalCenter
        text: "Y"
        muted: true
    }
    Coordinate {
        visible: row.explicit !== null
        value: row.explicit ? row.explicit.y : 0
        onCommitted: v => row.store.moveMonitor(row.name, row.explicit.x, v)
    }
}
