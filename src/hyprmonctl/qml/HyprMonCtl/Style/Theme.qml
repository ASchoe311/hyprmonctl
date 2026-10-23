pragma Singleton
import QtQuick

// Design tokens. Defaults follow COSMIC's dark Displays page; `applyPalette` maps a
// matugen/Material You color set (as produced for Quickshell shells) onto them.
QtObject {
    id: theme

    property color background: "#1b1b1b"
    property color surface: "#2b2b2b"          // cards
    property color surfaceHigh: "#343434"      // inputs, hovered rows
    property color surfaceHighest: "#3d3d3d"   // popups, pressed states
    property color divider: "#3a3a3a"
    property color text: "#e4e4e4"
    property color textMuted: "#a3a3a3"
    property color accent: "#63d0df"
    property color accentText: "#00363d"
    property color error: "#ff8a80"
    property color warning: "#f2c46d"
    property color tile: "#4b4b4b"
    property color tileBorder: "#9e9e9e"
    property color badge: "#000000"
    property color badgeText: "#ffffff"
    property color scrim: "#99000000"

    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.16)
    readonly property color hover: Qt.rgba(text.r, text.g, text.b, 0.06)
    readonly property color pressed: Qt.rgba(text.r, text.g, text.b, 0.12)

    property string fontFamily: Qt.application.font.family
    property string monoFamily: "monospace"
    property int fontSize: 14
    property int fontSizeSmall: 12
    property int fontSizeLarge: 16
    property int fontSizeTitle: 26

    property int radius: 10
    property int radiusSmall: 6
    property int spacing: 12
    property int padding: 20
    property int rowHeight: 56
    property int controlHeight: 34
    property int animationDuration: 160

    function severityColor(severity) {
        return severity === "error" ? error : severity === "warning" ? warning : textMuted;
    }

    // `colors` uses matugen key names (camelCase): primary, onPrimary, surfaceContainer, ...
    function applyPalette(colors) {
        if (!colors || !colors.primary)
            return;
        const pick = (...keys) => {
            for (const key of keys)
                if (colors[key])
                    return colors[key];
            return undefined;
        };
        const assign = (prop, ...keys) => {
            const value = pick(...keys);
            if (value !== undefined)
                theme[prop] = value;
        };
        assign("background", "background", "surface");
        assign("surface", "surfaceContainer", "surfaceVariant");
        assign("surfaceHigh", "surfaceContainerHigh");
        assign("surfaceHighest", "surfaceContainerHighest");
        assign("divider", "outlineVariant");
        assign("text", "onSurface");
        assign("textMuted", "onSurfaceVariant");
        assign("accent", "primary");
        assign("accentText", "onPrimary");
        assign("error", "error");
        assign("tile", "surfaceContainerHighest", "surfaceVariant");
        assign("tileBorder", "outline");
    }
}
