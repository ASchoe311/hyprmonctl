import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls
import HyprMonCtl.Layout
import "Format.js" as Format

// Scale as a coarse choice plus fine steps, COSMIC style. Only scales Hyprland accepts
// for the current mode (whole logical pixels) are offered; the backend computes them.
ColumnLayout {
    id: root

    required property var store
    required property string name
    readonly property var entry: store.entry(name)
    readonly property var config: store.config(name)
    readonly property bool automatic: config ? config.scale === "auto" : true
    readonly property var mode: entry && config ? Geometry.effectiveMode(entry, config) : null
    readonly property var resolution: entry && mode ? entry.resolutions.find(r => r.width === mode.width && r.height === mode.height) || null : null
    readonly property var validScales: resolution ? resolution.scales : []
    readonly property var niceScales: resolution ? resolution.niceScales.filter(s => s >= 0.75) : [1]
    readonly property real current: entry && config ? Geometry.effectiveScale(entry, config) : 1
    readonly property real base: {
        let b = niceScales.length ? niceScales[0] : 1;
        for (const s of niceScales)
            if (s <= current + 1e-6)
                b = s;
        return b;
    }
    readonly property var logical: entry && config ? Geometry.logicalSize(entry, config) : null
    readonly property var scaleIssue: store.issuesFor(name, ["invalid-scale"])[0] || null

    Layout.fillWidth: true
    spacing: 0

    SettingsRow {
        label: "Scale"
        caption: root.scaleIssue ? root.scaleIssue.message : root.logical ? "Looks like " + Format.resolution(root.logical.width, root.logical.height) + (root.automatic ? " · chosen by Hyprland" : "") : ""
        captionColor: root.scaleIssue ? Theme.error : Theme.textMuted

        HComboBox {
            value: root.automatic ? "auto" : root.base
            options: {
                const opts = [{ text: root.automatic ? "Automatic (" + Format.percent(root.current) + ")" : "Automatic", value: "auto", detail: "Based on pixel density" }];
                for (const s of root.niceScales)
                    opts.push({ text: Format.percent(s), value: s });
                return opts;
            }
            onPicked: value => root.store.setField(root.name, "scale", value)
        }
    }

    SettingsRow {
        label: "Additional scale options"

        HStepper {
            enabled: !root.automatic && root.validScales.length > 0
            readonly property real offset: root.current - root.base
            text: root.automatic ? "—" : (offset >= 0 ? "+" : "−") + Math.round(Math.abs(offset) * 100) + "%"
            canDecrease: root.validScales.some(s => s < root.current - 1e-6)
            canIncrease: root.validScales.some(s => s > root.current + 1e-6)
            onDecrease: {
                const lower = root.validScales.filter(s => s < root.current - 1e-6);
                root.store.setField(root.name, "scale", lower[lower.length - 1]);
            }
            onIncrease: root.store.setField(root.name, "scale", root.validScales.find(s => s > root.current + 1e-6))
        }
    }
}
