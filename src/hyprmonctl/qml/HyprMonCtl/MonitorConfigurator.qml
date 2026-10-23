import QtQuick
import QtQuick.Controls.Basic as T
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls
import HyprMonCtl.Panels
import HyprMonCtl.Dialogs

// The complete display settings page. Embed it anywhere and give it a transport:
//
//     MonitorConfigurator { anchors.fill: parent; transport: myTransport }
//
// A transport is any object with `send(string)` and a `messageReceived(string)` signal.
Item {
    id: root

    property var transport: null
    property bool showHeader: true
    property bool followShellTheme: true
    readonly property alias store: store

    MonitorStore {
        id: store
        transport: root.transport
        onMessage: (text, kind) => toast.show(text, kind)
    }

    Component.onCompleted: Qt.callLater(loadTheme)
    onTransportChanged: Qt.callLater(loadTheme)

    function showLua() { luaDialog.show(); }
    function showSettings() { settingsDialog.show(); }
    function loadTheme() {
        if (followShellTheme && transport)
            store.rpc.call("theme.get", {}, r => Theme.applyPalette(r.colors));
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.background
    }

    T.ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        visible: store.state !== null

        ColumnLayout {
            id: page
            width: Math.min(scroll.availableWidth - 48, 960)
            x: (scroll.availableWidth - width) / 2
            spacing: 16

            Item { Layout.preferredHeight: 8 }

            RowLayout {
                visible: root.showHeader
                Layout.fillWidth: true
                spacing: 8

                HLabel {
                    Layout.fillWidth: true
                    Layout.minimumWidth: implicitWidth
                    text: "Displays"
                    font.pixelSize: Theme.fontSizeTitle
                    font.weight: Font.Bold
                }
                T.AbstractButton {
                    id: fileChip
                    Layout.minimumWidth: 120
                    Layout.maximumWidth: page.width * 0.55
                    Layout.preferredWidth: implicitWidth
                    hoverEnabled: true
                    implicitHeight: 34
                    implicitWidth: chipIcon.width + chipLabel.implicitWidth + 44
                    onClicked: settingsDialog.show()
                    T.ToolTip.visible: hovered
                    T.ToolTip.delay: 500
                    T.ToolTip.text: (store.state ? store.state.luaPath + "\n" : "") + "Click to change which file is written"
                    background: Rectangle {
                        radius: height / 2
                        color: fileChip.hovered ? Theme.surfaceHigh : Theme.surface
                    }
                    contentItem: Item {
                        Icon {
                            id: chipIcon
                            anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                            name: "file"
                            size: 16
                            color: Theme.textMuted
                        }
                        HLabel {
                            id: chipLabel
                            anchors { left: chipIcon.right; leftMargin: 8; right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                            text: store.state ? store.state.luaPathDisplay : ""
                            elide: Text.ElideMiddle
                            font.family: Theme.monoFamily
                            font.pixelSize: Theme.fontSizeSmall
                            muted: true
                        }
                    }
                }
                HIconButton {
                    iconName: "code"
                    tooltip: "View the generated Lua"
                    onClicked: luaDialog.show()
                }
                HIconButton {
                    iconName: "settings"
                    tooltip: "Settings"
                    onClicked: settingsDialog.show()
                }
            }

            DiagnosticsBanner {
                diagnostics: store.diagnostics
            }

            ArrangementCard {
                store: store
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                MonitorTabs {
                    store: store
                }
                Item { Layout.preferredHeight: 12 }
                MonitorSettingsPanel {
                    visible: store.selectedName.length > 0
                    store: store
                    name: store.selectedName
                }
            }

            SavedRulesCard {
                store: store
            }

            // Room so the action bar never covers the last card.
            Item { Layout.preferredHeight: actionBar.height + 40 }
        }
    }

    // --- sticky action bar -------------------------------------------------------------

    Rectangle {
        id: actionBar
        readonly property bool shown: store.dirty && !store.previewActive

        anchors.horizontalCenter: parent.horizontalCenter
        y: shown ? parent.height - height - 20 : parent.height + 10
        width: Math.min(page.width, parent.width - 32)
        height: 64
        radius: Theme.radius + 4
        color: Theme.surfaceHighest
        border.color: Theme.divider
        visible: y < parent.height
        Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 12
            spacing: 8

            Icon {
                name: store.errors.length ? "alert" : "info"
                color: store.errors.length ? Theme.error : Theme.accent
            }
            HLabel {
                Layout.fillWidth: true
                text: store.errors.length === 1 ? "1 problem to fix before applying" : store.errors.length > 1 ? store.errors.length + " problems to fix before applying" : "Unsaved changes"
                color: store.errors.length ? Theme.error : Theme.text
            }
            HButton {
                text: "Discard"
                variant: "text"
                onClicked: store.discard()
            }
            HButton {
                text: "View Lua"
                iconName: "code"
                onClicked: luaDialog.show()
            }
            HButton {
                text: "Apply"
                variant: "primary"
                enabled: store.canApply
                onClicked: store.apply()
            }
        }
    }

    // --- loading / connection error ----------------------------------------------------

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 480)
        visible: store.state === null
        spacing: 16

        Icon {
            Layout.alignment: Qt.AlignHCenter
            name: store.loadError ? "alert" : "monitor"
            size: 40
            color: store.loadError ? Theme.error : Theme.textMuted
        }
        HLabel {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: store.loadError ? "Couldn't load the display configuration" : "Loading displays…"
            font.pixelSize: Theme.fontSizeLarge
        }
        HLabel {
            Layout.fillWidth: true
            visible: store.loadError.length > 0
            horizontalAlignment: Text.AlignHCenter
            text: store.loadError
            muted: true
            wrapMode: Text.Wrap
            elide: Text.ElideNone
        }
        HButton {
            Layout.alignment: Qt.AlignHCenter
            visible: store.loadError.length > 0
            text: "Retry"
            iconName: "refresh"
            onClicked: store.refresh(false)
        }
    }

    ConfirmChangesDialog {
        store: store
    }
    LuaPreviewDialog {
        id: luaDialog
        store: store
    }
    SettingsDialog {
        id: settingsDialog
        store: store
    }
    Toast {
        id: toast
    }
}
