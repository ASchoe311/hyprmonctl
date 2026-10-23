import QtQuick
import HyprMonCtl.Style
import HyprMonCtl.Controls

// The `output` string Hyprland uses to find this display (connector name or desc: prefix).
SettingsRow {
    id: row

    required property var store
    required property string name
    readonly property var entry: store.entry(name)
    readonly property var config: store.config(name)
    readonly property var problems: store.issuesFor(name, ["empty-output", "output-mismatch", "duplicate-output", "output-ambiguous"])
    property bool editing: false

    label: "Identify by"
    caption: {
        if (problems.length)
            return problems[0].message;
        if (!config || !entry)
            return "";
        return config.output === entry.defaultIdentifier ? "Matches only this display (recommended)" : "Matches only this display";
    }
    captionColor: problems.length ? Theme.severityColor(problems[0].severity) : Theme.textMuted

    HComboBox {
        visible: !row.editing
        value: row.config ? row.config.output : ""
        options: {
            if (!row.entry || !row.config)
                return [];
            const opts = row.entry.identifiers.map(c => ({
                text: c.value,
                value: c.value,
                detail: c.label + (c.unique ? "" : " · also matches other displays")
            }));
            const current = row.config.output;
            if (!opts.some(o => o.value === current))
                opts.push({ text: current, value: current, detail: "Custom" });
            opts.push({ text: "Custom…", value: "\u0000custom", detail: "Any connector name or desc: prefix" });
            return opts;
        }
        onPicked: value => {
            if (value === "\u0000custom") {
                field.text = row.config.output;
                row.editing = true;
                field.forceActiveFocus();
                field.selectAll();
            } else {
                row.store.setField(row.name, "output", value);
            }
        }
    }

    HTextField {
        id: field
        visible: row.editing
        width: 340
        monospace: true
        placeholderText: "desc:Make Model Serial  or  DP-1"
        onAccepted: {
            row.store.setField(row.name, "output", text.trim());
            row.editing = false;
        }
        Keys.onEscapePressed: row.editing = false
        onActiveFocusChanged: if (!activeFocus && row.editing) accepted()
    }
}
