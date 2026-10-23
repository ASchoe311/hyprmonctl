.pragma library

// Pure geometry helpers for the arrangement canvas. They mirror the backend's
// `model/draft.py` effective-geometry rules so dragging gets instant feedback; the
// backend's `layout.validate` stays authoritative for errors.

function parseMode(text) {
    const m = /^\s*(\d+)\s*x\s*(\d+)\s*(?:@\s*([\d.]+))?/i.exec(text || "");
    return m ? { width: +m[1], height: +m[2], refresh: m[3] ? +m[3] : 0 } : null;
}

function parsePosition(text) {
    const m = /^\s*(-?\d+)\s*x\s*(-?\d+)\s*$/.exec(text || "");
    return m ? { x: +m[1], y: +m[2] } : null;
}

function formatPosition(x, y) {
    return Math.round(x) + "x" + Math.round(y);
}

// The mode a config produces: special names resolve via the monitor's advertised modes.
function effectiveMode(entry, config) {
    if (entry.specialModes[config.mode])
        return parseMode(entry.specialModes[config.mode]);
    return parseMode(config.mode) || { width: entry.live.width, height: entry.live.height, refresh: entry.live.refreshRate };
}

function effectiveScale(entry, config) {
    if (typeof config.scale === "number" && config.scale > 0)
        return config.scale;
    return !entry.live.disabled && entry.live.scale > 0 ? entry.live.scale : 1;
}

function logicalSize(entry, config) {
    const mode = effectiveMode(entry, config);
    const scale = effectiveScale(entry, config);
    const w = Math.round(mode.width / scale), h = Math.round(mode.height / scale);
    return config.transform % 2 === 1 ? { width: h, height: w } : { width: w, height: h };
}

// Rects for every displayable monitor: enabled and not mirroring another output.
function layoutRects(entries, configs) {
    const rects = [];
    const pending = [];
    for (let i = 0; i < entries.length; ++i) {
        const entry = entries[i], config = configs[i];
        if (!config || !config.enabled || config.mirror)
            continue;
        const size = logicalSize(entry, config);
        let pos = parsePosition(config.position);
        if (!pos && !entry.live.disabled)
            pos = { x: entry.live.x, y: entry.live.y };
        const rect = { name: entry.name, number: entry.id + 1, auto: !parsePosition(config.position), width: size.width, height: size.height };
        if (pos) {
            rect.x = pos.x;
            rect.y = pos.y;
            rects.push(rect);
        } else {
            pending.push(rect);
        }
    }
    for (const rect of pending) {
        const b = bounds(rects);
        rect.x = rects.length ? b.x + b.width : 0;
        rect.y = rects.length ? b.y : 0;
        rects.push(rect);
    }
    return rects;
}

function bounds(rects) {
    if (!rects.length)
        return { x: 0, y: 0, width: 1920, height: 1080 };
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const r of rects) {
        x1 = Math.min(x1, r.x);
        y1 = Math.min(y1, r.y);
        x2 = Math.max(x2, r.x + r.width);
        y2 = Math.max(y2, r.y + r.height);
    }
    return { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
}

function overlaps(a, b) {
    return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

// Left-to-right, top-aligned arrangement in the current visual order.
function arrangeRow(rects) {
    const sorted = rects.slice().sort((a, b) => a.x - b.x || a.y - b.y);
    const out = {};
    let x = sorted.length ? Math.min(...sorted.map(r => r.x)) : 0;
    const y = sorted.length ? Math.min(...sorted.map(r => r.y)) : 0;
    for (const r of sorted) {
        out[r.name] = { x: x, y: y };
        x += r.width;
    }
    return out;
}
