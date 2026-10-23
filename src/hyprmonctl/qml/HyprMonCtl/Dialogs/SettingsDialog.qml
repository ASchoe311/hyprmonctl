import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls

ModalDialog {
    id: dialog

    required property var store
    property string error

    title: "Settings"
    dialogWidth: 600

    function show() {
        const s = store.settings;
        luaPath.text = s.luaPath || "";
        themePath.text = s.themeColorsPath || "";
        timeout.value = s.confirmTimeout || 15;
        reload.checked = s.reloadAfterSave !== false;
        backup.checked = s.backup !== false;
        error = "";
        open = true;
    }

    function save() {
        store.updateSettings({
            luaPath: luaPath.text.trim(),
            themeColorsPath: themePath.text.trim(),
            confirmTimeout: timeout.value,
            reloadAfterSave: reload.checked,
            backup: backup.checked
        }, err => {
            error = err;
            if (!err)
                close();
        });
    }

    component Field: ColumnLayout {
        id: field
        property string label
        property string hint
        default property alias content: row.data
        Layout.fillWidth: true
        spacing: 6
        HLabel { text: field.label; font.weight: Font.DemiBold }
        RowLayout {
            id: row
            Layout.fillWidth: true
            spacing: 8
        }
        HLabel {
            Layout.fillWidth: true
            visible: field.hint.length > 0
            text: field.hint
            muted: true
            font.pixelSize: Theme.fontSizeSmall
            wrapMode: Text.Wrap
            elide: Text.ElideNone
        }
    }

    Field {
        label: "Monitor config file"
        hint: "The Lua file hyprmonctl writes. Hyprland must load it, e.g. with require(\"config.monitors\") in hyprland.lua."
        HTextField {
            id: luaPath
            Layout.fillWidth: true
            monospace: true
            invalid: dialog.error.toLowerCase().indexOf("luapath") >= 0
            onAccepted: dialog.save()
        }
        HButton {
            text: "Browse…"
            visible: picker.status === Loader.Ready
            onClicked: picker.item.open() // qmllint disable missing-property
        }
        Loader {
            id: picker
            source: Qt.resolvedUrl("FilePicker.qml")
        }
        Connections {
            target: picker.item
            ignoreUnknownSignals: true
            function onAccepted() {
                // qmllint disable missing-property
                luaPath.text = decodeURIComponent(String(picker.item.selectedFile).replace(/^file:\/\//, ""));
            }
        }
    }

    Field {
        label: "Revert after"
        hint: "How long a live preview waits for you to keep it."
        HComboBox {
            id: timeout
            Layout.alignment: Qt.AlignLeft
            options: [10, 15, 20, 30, 60].map(s => ({ text: s + " seconds", value: s }))
            onPicked: v => timeout.value = v
        }
    }

    RowLayout {
        Layout.fillWidth: true
        HLabel { Layout.fillWidth: true; text: "Reload Hyprland after saving" }
        HSwitch {
            id: reload
            onClicked: checked = !checked
        }
    }
    RowLayout {
        Layout.fillWidth: true
        HLabel { Layout.fillWidth: true; text: "Keep a backup (.bak) of the previous file" }
        HSwitch {
            id: backup
            onClicked: checked = !checked
        }
    }

    Field {
        label: "Theme colors"
        hint: "A matugen-style colors.json to follow your shell's palette. Leave empty for the built-in theme."
        HTextField {
            id: themePath
            Layout.fillWidth: true
            monospace: true
            onAccepted: dialog.save()
        }
    }

    HLabel {
        Layout.fillWidth: true
        visible: dialog.error.length > 0
        text: dialog.error
        color: Theme.error
        wrapMode: Text.Wrap
        elide: Text.ElideNone
    }

    buttons: [
        HButton {
            text: "Cancel"
            onClicked: dialog.close()
        },
        HButton {
            text: "Save"
            variant: "primary"
            onClicked: dialog.save()
        }
    ]
}
