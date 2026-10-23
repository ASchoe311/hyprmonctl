import QtQuick
import QtQuick.Shapes
import HyprMonCtl.Style
import "Icons.js" as Icons

Item {
    id: root

    property string name
    property color color: Theme.text
    property real size: 18
    property real strokeWidth: 2

    implicitWidth: size
    implicitHeight: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: root.color
            strokeWidth: root.strokeWidth
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: Icons.paths[root.name] || "" }
        }
    }
}
