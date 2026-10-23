pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic as T
import HyprMonCtl.Style

// Flat dropdown: "value ▾" like COSMIC. `options` is an array of
// { text, value, detail? }; `value` selects the matching option.
T.ComboBox {
    id: control

    property var options: []
    property var value
    property int minimumContentWidth: 0
    signal picked(var value)

    model: options
    textRole: "text"
    valueRole: "value"

    // currentIndex is assigned imperatively: the control overwrites it on activation,
    // which would break a declarative binding to `value`.
    function sync() { currentIndex = indexOf(value); }
    onValueChanged: sync()
    onOptionsChanged: Qt.callLater(sync)
    onCountChanged: sync()
    Component.onCompleted: sync()
    onActivated: index => {
        picked(options[index].value);
        Qt.callLater(sync);
    }

    function indexOf(v) {
        for (let i = 0; i < options.length; ++i)
            if (options[i].value === v)
                return i;
        return -1;
    }

    FontMetrics {
        id: fontMetrics
        font: control.font
    }

    implicitHeight: Theme.controlHeight
    implicitWidth: Math.min(420, Math.max(minimumContentWidth, contentText.implicitWidth) + leftPadding + rightPadding)
    leftPadding: 10
    rightPadding: 36
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontSize
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusSmall
        color: control.pressed ? Theme.pressed : control.hovered && control.enabled ? Theme.hover : "transparent"
    }

    contentItem: HLabel {
        id: contentText
        text: control.currentIndex >= 0 ? control.displayText : (control.value !== undefined && control.value !== null ? String(control.value) : "")
        horizontalAlignment: Text.AlignRight
        opacity: control.enabled ? 1 : 0.5
    }

    indicator: Icon {
        x: control.width - width - 10
        y: (control.height - height) / 2
        name: "chevron-down"
        size: 16
        opacity: control.enabled ? 1 : 0.5
    }

    delegate: T.ItemDelegate {
        id: item
        required property var modelData
        required property int index
        width: ListView.view ? ListView.view.width : implicitWidth
        implicitHeight: modelData.detail ? 48 : 38
        hoverEnabled: true
        highlighted: control.highlightedIndex === item.index

        background: Rectangle {
            radius: Theme.radiusSmall
            color: item.highlighted || item.hovered ? Theme.hover : "transparent"
        }
        contentItem: Item {
            implicitWidth: textColumn.implicitWidth + 40
            Column {
                id: textColumn
                anchors { left: parent.left; right: check.left; verticalCenter: parent.verticalCenter; leftMargin: 6 }
                HLabel {
                    width: parent.width
                    text: item.modelData.text
                    color: control.currentIndex === item.index ? Theme.accent : Theme.text
                }
                HLabel {
                    width: parent.width
                    visible: !!item.modelData.detail
                    text: item.modelData.detail || ""
                    muted: true
                    font.pixelSize: Theme.fontSizeSmall
                }
            }
            Icon {
                id: check
                anchors { right: parent.right; verticalCenter: parent.verticalCenter; rightMargin: 4 }
                name: "check"
                size: 16
                color: Theme.accent
                visible: control.currentIndex === item.index
            }
        }
    }

    popup: T.Popup {
        y: control.height + 4
        x: control.width - width
        width: Math.max(control.width, Math.min(460, list.contentItemWidth + 24))
        implicitHeight: Math.min(list.contentHeight + 12, 360)
        padding: 6

        background: Rectangle {
            radius: Theme.radius
            color: Theme.surfaceHighest
            border.color: Theme.divider
        }
        contentItem: ListView {
            id: list
            readonly property real contentItemWidth: {
                let widest = 0;
                for (let i = 0; i < control.options.length; ++i)
                    widest = Math.max(widest, fontMetrics.advanceWidth(control.options[i].text), fontMetrics.advanceWidth(control.options[i].detail || ""));
                return widest + 40;
            }
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            T.ScrollIndicator.vertical: T.ScrollIndicator {}
        }
    }
}
