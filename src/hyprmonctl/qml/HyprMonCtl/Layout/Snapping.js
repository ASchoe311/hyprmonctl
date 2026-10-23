.pragma library

// Snap a dragged rect to the edges/centers of the other monitors.
// `threshold` is in layout pixels. Returns { x, y, guides: [{ axis: "x"|"y", at }] }.
function snap(rect, others, threshold) {
    let best = { x: null, dx: threshold + 1, y: null, dy: threshold + 1, gx: null, gy: null };

    function tryX(candidate, guide) {
        const d = Math.abs(candidate - rect.x);
        if (d < best.dx) {
            best.dx = d;
            best.x = candidate;
            best.gx = guide;
        }
    }
    function tryY(candidate, guide) {
        const d = Math.abs(candidate - rect.y);
        if (d < best.dy) {
            best.dy = d;
            best.y = candidate;
            best.gy = guide;
        }
    }

    for (const o of others) {
        const oRight = o.x + o.width, oBottom = o.y + o.height;
        // Side by side (edges touching), then aligned edges and centers.
        tryX(oRight, oRight);
        tryX(o.x - rect.width, o.x);
        tryX(o.x, o.x);
        tryX(oRight - rect.width, oRight);
        tryX(o.x + (o.width - rect.width) / 2, o.x + o.width / 2);
        tryY(oBottom, oBottom);
        tryY(o.y - rect.height, o.y);
        tryY(o.y, o.y);
        tryY(oBottom - rect.height, oBottom);
        tryY(o.y + (o.height - rect.height) / 2, o.y + o.height / 2);
    }

    const guides = [];
    let x = rect.x, y = rect.y;
    if (best.x !== null && best.dx <= threshold) {
        x = best.x;
        guides.push({ axis: "x", at: best.gx });
    }
    if (best.y !== null && best.dy <= threshold) {
        y = best.y;
        guides.push({ axis: "y", at: best.gy });
    }
    return { x: Math.round(x), y: Math.round(y), guides: guides };
}

function _overlaps(a, b) {
    return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

function _touches(a, b) {
    const vertical = (a.x + a.width === b.x || b.x + b.width === a.x) && Math.min(a.y + a.height, b.y + b.height) > Math.max(a.y, b.y);
    const horizontal = (a.y + a.height === b.y || b.y + b.height === a.y) && Math.min(a.x + a.width, b.x + b.width) > Math.max(a.x, b.x);
    return vertical || horizontal;
}

// After a drop: if the rect floats free or overlaps, move it to the nearest spot where it
// shares an edge with another monitor without overlapping any (Hyprland needs adjacency
// for the cursor to cross between displays).
function attach(rect, others) {
    if (!others.length)
        return { x: rect.x, y: rect.y };
    const free = !others.some(o => _overlaps(rect, o));
    if (free && others.some(o => _touches(rect, o)))
        return { x: rect.x, y: rect.y };

    let best = null;
    for (const o of others) {
        const y = Math.min(Math.max(rect.y, o.y - rect.height + 1), o.y + o.height - 1);
        const x = Math.min(Math.max(rect.x, o.x - rect.width + 1), o.x + o.width - 1);
        const candidates = [
            { x: o.x + o.width, y: y }, { x: o.x - rect.width, y: y },
            { x: x, y: o.y + o.height }, { x: x, y: o.y - rect.height }
        ];
        for (const c of candidates) {
            const placed = { x: c.x, y: c.y, width: rect.width, height: rect.height };
            if (others.some(other => _overlaps(placed, other)))
                continue;
            const d = Math.hypot(c.x - rect.x, c.y - rect.y);
            if (!best || d < best.d)
                best = { x: c.x, y: c.y, d: d };
        }
    }
    return best ? { x: Math.round(best.x), y: Math.round(best.y) } : { x: rect.x, y: rect.y };
}
