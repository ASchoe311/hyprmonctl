pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls

// Rules in the file that don't configure a connected display (other desks, fallback).
// They are written back untouched unless removed here.
Card {
    id: card

    required property var store
    readonly property var rules: store.savedRules.filter(r => store.keepRules.indexOf(r.index) >= 0)
    readonly property int removed: store.savedRules.length - rules.length

    readonly property var statusText: ({
        "disconnected": "Not connected",
        "fallback": "Used for any display without its own rule",
        "overridden": "Overridden by a later rule"
    })

    Layout.fillWidth: true
    visible: store.savedRules.length > 0
    title: "Saved for other displays"

    Repeater {
        model: card.rules

        delegate: SettingsRow {
            id: ruleRow
            required property var modelData
            required property int index
            showDivider: index > 0
            label: modelData.output || "Any other display"
            caption: {
                const parts = [card.statusText[modelData.status] || modelData.status];
                if (modelData.disabled)
                    parts.push("disabled");
                for (const v of [modelData.mode, modelData.position, modelData.scale ? "scale " + modelData.scale : null])
                    if (v)
                        parts.push(v);
                return parts.join(" · ");
            }

            HIconButton {
                iconName: "trash"
                tooltip: "Remove from the config file"
                onClicked: card.store.removeSavedRule(ruleRow.modelData.index)
            }
        }
    }

    SettingsRow {
        visible: card.removed > 0
        showDivider: card.rules.length > 0
        label: card.removed === 1 ? "1 rule will be removed when you apply" : card.removed + " rules will be removed when you apply"
        HButton {
            variant: "text"
            text: "Undo"
            onClicked: card.store.restoreSavedRules()
        }
    }
}
