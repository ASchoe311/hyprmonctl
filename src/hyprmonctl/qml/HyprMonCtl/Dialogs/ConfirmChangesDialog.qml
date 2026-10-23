import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import HyprMonCtl.Style
import HyprMonCtl.Controls

// "Keep these settings?" with a countdown that mirrors the backend's revert timer.
ModalDialog {
    id: dialog

    required property var store
    property real remaining: 0

    open: store.previewActive
    dismissable: false
    dialogWidth: 440
    title: "Keep these display settings?"

    Timer {
        running: dialog.open
        interval: 100
        repeat: true
        triggeredOnStart: true
        onTriggered: dialog.remaining = Math.max(0, dialog.store.previewDeadline - Date.now() / 1000)
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spacing + 4

        Item {
            implicitWidth: 64
            implicitHeight: 64

            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeColor: Theme.surfaceHighest
                    strokeWidth: 5
                    fillColor: "transparent"
                    PathAngleArc { centerX: 32; centerY: 32; radiusX: 28; radiusY: 28; startAngle: 0; sweepAngle: 360 }
                }
                ShapePath {
                    strokeColor: Theme.accent
                    strokeWidth: 5
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathAngleArc {
                        centerX: 32
                        centerY: 32
                        radiusX: 28
                        radiusY: 28
                        startAngle: -90
                        sweepAngle: dialog.store.previewTimeout > 0 ? 360 * dialog.remaining / dialog.store.previewTimeout : 0
                    }
                }
            }
            HLabel {
                anchors.centerIn: parent
                text: Math.ceil(dialog.remaining)
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
        }

        HLabel {
            Layout.fillWidth: true
            text: "The new layout is active. If you can't see this, it will revert to the previous settings automatically."
            wrapMode: Text.Wrap
            elide: Text.ElideNone
            muted: true
        }
    }

    buttons: [
        HButton {
            text: "Revert"
            iconName: "undo"
            enabled: !dialog.store.busy
            onClicked: dialog.store.revert()
        },
        HButton {
            text: "Keep changes"
            variant: "primary"
            iconName: "check"
            enabled: !dialog.store.busy
            onClicked: dialog.store.keep()
        }
    ]
}
