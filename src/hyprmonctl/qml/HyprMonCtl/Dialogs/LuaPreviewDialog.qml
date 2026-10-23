import QtQuick
import QtQuick.Controls.Basic as T
import QtQuick.Layouts
import HyprMonCtl.Style
import HyprMonCtl.Controls

// The exact Lua that applying would write, for review or copying.
ModalDialog {
    id: dialog

    required property var store
    property string lua
    property string error

    title: store.state ? store.state.luaPathDisplay : "Generated Lua"
    dialogWidth: 720

    function show() {
        lua = "";
        error = "";
        open = true;
        store.renderLua((text, err) => {
            lua = text;
            error = err;
        });
    }

    HLabel {
        Layout.fillWidth: true
        visible: dialog.error.length > 0
        text: dialog.error
        color: Theme.error
        wrapMode: Text.Wrap
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.preferredHeight: Math.min(text.implicitHeight + 24, 460)
        radius: Theme.radiusSmall
        color: Theme.background

        T.ScrollView {
            anchors.fill: parent
            anchors.margins: 12
            clip: true

            T.TextArea {
                id: text
                text: dialog.lua
                readOnly: true
                selectByMouse: true
                color: Theme.text
                selectionColor: Theme.accent
                selectedTextColor: Theme.accentText
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fontSizeSmall + 1
                wrapMode: TextEdit.NoWrap
                background: null
                padding: 0
            }
        }
    }

    buttons: [
        HButton {
            text: "Copy"
            iconName: "copy"
            enabled: dialog.lua.length > 0
            onClicked: {
                text.selectAll();
                text.copy();
                text.deselect();
            }
        },
        HButton {
            text: "Close"
            variant: "primary"
            onClicked: dialog.close()
        }
    ]
}
