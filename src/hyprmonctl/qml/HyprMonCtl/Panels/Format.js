.pragma library

function percent(scale) {
    return Math.round(scale * 100) + "%";
}

function resolution(width, height) {
    return width + " × " + height;
}

function hz(rate) {
    return rate.toFixed(2) + " Hz";
}

function aspect(width, height) {
    const gcd = (a, b) => b ? gcd(b, a % b) : a;
    const d = gcd(width, height);
    const w = width / d, h = height / d;
    // Name the common "near" ratios the way people know them.
    if (w === 8 && h === 5) return "16:10";
    if (w === 43 && h === 18 || w === 64 && h === 27) return "21:9";
    return w + ":" + h;
}

// "1920x1080@100.00" -> "1920 × 1080 @ 100.00 Hz"
function modeText(mode) {
    const m = /^(\d+)x(\d+)(?:@([\d.]+))?/.exec(mode || "");
    if (!m)
        return mode || "";
    return resolution(+m[1], +m[2]) + (m[3] ? " @ " + hz(+m[3]) : "");
}

var transforms = [
    { text: "Standard", value: 0 },
    { text: "Rotated 90°", value: 1 },
    { text: "Rotated 180°", value: 2 },
    { text: "Rotated 270°", value: 3 },
    { text: "Flipped", value: 4 },
    { text: "Flipped, rotated 90°", value: 5 },
    { text: "Flipped, rotated 180°", value: 6 },
    { text: "Flipped, rotated 270°", value: 7 }
];

var autoPositions = [
    { text: "Automatic", value: "auto", detail: "Right of the other displays" },
    { text: "Auto · right", value: "auto-right" },
    { text: "Auto · left", value: "auto-left" },
    { text: "Auto · above", value: "auto-up" },
    { text: "Auto · below", value: "auto-down" },
    { text: "Auto · centered right", value: "auto-center-right" },
    { text: "Auto · centered left", value: "auto-center-left" },
    { text: "Auto · centered above", value: "auto-center-up" },
    { text: "Auto · centered below", value: "auto-center-down" }
];

var vrrModes = [
    { text: "Default", value: null, detail: "Follow misc:vrr" },
    { text: "Off", value: 0 },
    { text: "On", value: 1 },
    { text: "Fullscreen only", value: 2 },
    { text: "Fullscreen video/games", value: 3 }
];

var bitDepths = [
    { text: "Default", value: null },
    { text: "8-bit", value: 8 },
    { text: "10-bit", value: 10 }
];

var colorPresets = [
    { text: "Default", value: null },
    { text: "Auto", value: "auto", detail: "sRGB for 8-bit, wide for 10-bit" },
    { text: "sRGB", value: "srgb" },
    { text: "DCI-P3", value: "dcip3" },
    { text: "Display P3", value: "dp3" },
    { text: "Adobe RGB", value: "adobe" },
    { text: "Wide (BT.2020)", value: "wide" },
    { text: "EDID primaries", value: "edid" },
    { text: "HDR", value: "hdr", detail: "Experimental" },
    { text: "HDR, EDID primaries", value: "hdredid", detail: "Experimental" }
];
