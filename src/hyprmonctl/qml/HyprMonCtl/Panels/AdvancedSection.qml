import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls
import "Format.js" as Format

// Collapsible VRR / bit depth / color management settings. "Default" leaves the
// field out of the rule so Hyprland's global setting applies.
ColumnLayout {
    id: root

    required property var store
    required property string name
    readonly property var entry: store.entry(name)
    readonly property var config: store.config(name)
    property bool expanded: false

    Layout.fillWidth: true
    spacing: 0

    SettingsRow {
        label: "Advanced"
        caption: "Variable refresh rate, bit depth and color management"
        clickable: true
        onClicked: root.expanded = !root.expanded

        Icon {
            name: "chevron-down"
            rotation: root.expanded ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: Theme.animationDuration } }
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        visible: root.expanded
        spacing: 0

        SettingsRow {
            label: "Variable refresh rate"
            caption: root.entry ? "Currently " + (root.entry.live.vrr ? "active" : "inactive") : ""
            HComboBox {
                value: root.config ? root.config.vrr : null
                options: Format.vrrModes
                onPicked: value => root.store.setField(root.name, "vrr", value)
            }
        }
        SettingsRow {
            label: "Bit depth"
            caption: root.entry ? "Currently " + root.entry.live.bitdepth + "-bit" : ""
            HComboBox {
                value: root.config ? root.config.bitdepth : null
                options: Format.bitDepths
                onPicked: value => root.store.setField(root.name, "bitdepth", value)
            }
        }
        SettingsRow {
            label: "Color management"
            caption: root.entry && root.entry.live.colorPreset ? "Currently " + root.entry.live.colorPreset : ""
            HComboBox {
                value: root.config ? root.config.cm : null
                options: Format.colorPresets
                onPicked: value => root.store.setField(root.name, "cm", value)
            }
        }
    }
}
