import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls
import "Format.js" as Format

// All settings for one display, as a single card of rows.
Card {
    id: panel

    required property var store
    required property string name
    readonly property var entry: store.entry(name)
    readonly property var config: store.config(name)
    readonly property bool active: !!config && config.enabled
    readonly property bool mirroring: active && !!config.mirror

    Layout.fillWidth: true

    SettingsRow {
        showDivider: false
        label: "Enable display"
        caption: panel.entry ? panel.entry.description : ""

        HSwitch {
            checked: panel.active
            enabled: !panel.active || panel.store.enabledCount() > 1
            onClicked: panel.store.setField(panel.name, "enabled", !checked)
        }
    }

    IdentifierRow {
        store: panel.store
        name: panel.name
    }

    SettingsRow {
        enabled: panel.active
        opacity: enabled ? 1 : 0.5
        label: "Mirroring"
        caption: {
            const issue = panel.store.issuesFor(panel.name, ["bad-mirror"])[0];
            return issue ? issue.message : panel.mirroring ? "Shows the same picture as " + panel.config.mirror : "";
        }
        captionColor: panel.store.issuesFor(panel.name, ["bad-mirror"]).length ? Theme.error : Theme.textMuted

        HComboBox {
            value: panel.config ? panel.config.mirror : null
            options: {
                const opts = [{ text: "Don't mirror", value: null }];
                for (const m of panel.store.monitors)
                    if (m.name !== panel.name)
                        opts.push({ text: m.name, value: m.name, detail: m.label });
                if (panel.config && panel.config.mirror && !opts.some(o => o.value === panel.config.mirror))
                    opts.push({ text: panel.config.mirror, value: panel.config.mirror, detail: "Not connected" });
                return opts;
            }
            onPicked: value => panel.store.setField(panel.name, "mirror", value)
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 0
        enabled: panel.active && !panel.mirroring
        opacity: enabled ? 1 : 0.5

        ModeRows {
            store: panel.store
            name: panel.name
        }
        ScaleRows {
            store: panel.store
            name: panel.name
        }
        SettingsRow {
            label: "Orientation"
            HComboBox {
                value: panel.config ? panel.config.transform : 0
                options: Format.transforms
                onPicked: value => panel.store.setField(panel.name, "transform", value)
            }
        }
        PositionRow {
            store: panel.store
            name: panel.name
        }
        AdvancedSection {
            store: panel.store
            name: panel.name
        }
    }
}
