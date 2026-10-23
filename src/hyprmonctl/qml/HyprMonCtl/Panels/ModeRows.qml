import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls
import HyprMonCtl.Layout
import "Format.js" as Format

// Resolution + refresh rate, populated from the modes the display advertises.
ColumnLayout {
    id: root

    required property var store
    required property string name
    readonly property var entry: store.entry(name)
    readonly property var config: store.config(name)
    readonly property bool special: !!(entry && config && entry.specialModes[config.mode])
    readonly property var mode: entry && config ? Geometry.effectiveMode(entry, config) : null
    readonly property string resolutionKey: mode ? mode.width + "x" + mode.height : ""
    readonly property var resolution: entry ? entry.resolutions.find(r => r.width + "x" + r.height === resolutionKey) || null : null

    Layout.fillWidth: true
    spacing: 0

    function setMode(width, height, rate) {
        store.setField(name, "mode", width + "x" + height + "@" + rate.toFixed(2));
    }

    SettingsRow {
        label: "Resolution"
        caption: {
            const issue = root.store.issuesFor(root.name, ["mode-unavailable", "custom-mode"])[0];
            if (issue)
                return issue.message;
            return root.special && root.mode ? Format.resolution(root.mode.width, root.mode.height) + " · picked by Hyprland" : "";
        }
        captionColor: root.store.issuesFor(root.name, ["mode-unavailable"]).length ? Theme.warning : Theme.textMuted

        HComboBox {
            value: !root.config ? "" : root.special ? root.config.mode : root.resolution ? root.resolutionKey : root.config.mode
            options: {
                if (!root.entry || !root.config)
                    return [];
                const specials = root.entry.specialModes;
                const opts = [
                    { text: "Preferred", value: "preferred", detail: Format.modeText(specials.preferred) },
                    { text: "Highest resolution", value: "highres", detail: Format.modeText(specials.highres) },
                    { text: "Highest refresh rate", value: "highrr", detail: Format.modeText(specials.highrr) }
                ];
                const preferred = /^(\d+x\d+)/.exec(specials.preferred || "");
                for (const r of root.entry.resolutions) {
                    const key = r.width + "x" + r.height;
                    const native = preferred && preferred[1] === key;
                    opts.push({ text: Format.resolution(r.width, r.height), value: key, detail: Format.aspect(r.width, r.height) + (native ? " · native" : "") });
                }
                if (!root.special && !root.resolution)
                    opts.push({ text: root.config.mode, value: root.config.mode, detail: "Custom mode" });
                return opts;
            }
            onPicked: value => {
                if (root.entry.specialModes[value]) {
                    root.store.setField(root.name, "mode", value);
                    return;
                }
                const r = root.entry.resolutions.find(r => r.width + "x" + r.height === value);
                if (!r)
                    return;
                const current = root.mode ? root.mode.refresh : 0;
                const rate = r.refreshRates.find(rate => Math.abs(rate - current) < 0.05) || r.refreshRates[0];
                root.setMode(r.width, r.height, rate);
            }
        }
    }

    SettingsRow {
        label: "Refresh rate"

        HComboBox {
            enabled: !root.special && !!root.resolution
            value: root.mode ? root.mode.refresh : 0
            options: {
                if (root.special || !root.resolution)
                    return root.mode && root.mode.refresh ? [{ text: Format.hz(root.mode.refresh), value: root.mode.refresh }] : [];
                const rates = root.resolution.refreshRates.map(rate => ({ text: Format.hz(rate), value: rate }));
                if (root.mode.refresh && !rates.some(r => Math.abs(r.value - root.mode.refresh) < 0.005))
                    rates.unshift({ text: Format.hz(root.mode.refresh), value: root.mode.refresh, detail: "Not advertised" });
                return rates;
            }
            onPicked: value => root.setMode(root.mode.width, root.mode.height, value)
        }
    }
}
