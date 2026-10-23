pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls
import HyprMonCtl.Layout

Card {
    id: card

    required property var store
    readonly property var layoutIssues: store.issues.filter(i => ["overlap", "detached", "all-disabled"].indexOf(i.code) >= 0)

    Layout.fillWidth: true
    title: "Drag displays to rearrange them"
    headerActions: [
        HIconButton {
            iconName: "arrange"
            tooltip: "Arrange side by side"
            onClicked: card.store.arrangeRow()
        }
    ]

    LayoutCanvas {
        Layout.fillWidth: true
        Layout.preferredHeight: 230
        store: card.store
        snapDistance: card.store.settings.snapDistance || 16
    }

    Repeater {
        model: card.layoutIssues

        delegate: RowLayout {
            id: issueRow
            required property var modelData
            Layout.fillWidth: true
            Layout.leftMargin: Theme.padding + 8
            Layout.rightMargin: Theme.padding
            Layout.bottomMargin: 6
            spacing: 8

            Icon {
                name: "alert"
                size: 16
                color: Theme.severityColor(issueRow.modelData.severity)
            }
            HLabel {
                Layout.fillWidth: true
                text: issueRow.modelData.message
                color: Theme.severityColor(issueRow.modelData.severity)
                font.pixelSize: Theme.fontSizeSmall
                wrapMode: Text.Wrap
            }
        }
    }

    Item {
        Layout.preferredHeight: 10
    }
}
