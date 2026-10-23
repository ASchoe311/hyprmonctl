# Layout/: arrangement canvas

| File | Role |
|---|---|
| `LayoutCanvas.qml` | Holds the view transform (`zoom`, `offsetX/Y`). `rects` comes from `Geometry.layoutRects(store.monitors, store.configs)`. `refit()` zoom-to-fits the bounding box with `margin`. Draws snap `guides`. The Repeater model is `store.monitors` (stable), so tiles aren't recreated on every edit. |
| `MonitorTile.qml` | One display: number pill (Hyprland id + 1), connector caption and `AUTO` badge when there's room, overlap tint. Handles the drag. |
| `Geometry.js` | Effective mode, scale, logical size and auto placement, mirroring `model/draft.py` and `model/layout.py`. Keep them consistent. Also `bounds`, `overlaps`, `arrangeRow`, position parse/format. |
| `Snapping.js` | `snap(rect, others, threshold)` aligns to edges, adjacent edges and centers. `attach(rect, others)` runs on drop: if the rect floats free or overlaps, it moves to the nearest edge-sharing, non-overlapping spot. |

## Coordinates and drag

- **Rects are in layout coordinates** (Hyprland logical px). Screen position is
  `offset + layout * zoom`.
- **During a drag** (`view.dragging`), `refit()` is suppressed, so the scene doesn't
  shift under the cursor. The tile shows `dragX/dragY` instead of its rect. On
  release, `attach` runs, then `store.moveMonitor`, then the view refits (animated).
- **Snap threshold** is `snapDistance` (screen px, a setting) divided by `zoom`.
- **The tile's `MouseArea` has `preventStealing: true`**, because the page ScrollView
  would otherwise cancel vertical drags.
- **`refit()` computes offsets from a local zoom value.** `zoom` has a `Behavior`, so
  reading it back right after assigning returns the animated value. That bug
  misplaced everything when there were many monitors.
- **Monitors left off the canvas:** disabled and mirroring monitors.
- **Auto-placed monitors** use their live position, or sit to the right of the others
  if they're live-disabled.

Tested at scale with 7 monitors (5 headless outputs); see the `hyprmonctl-verify`
skill, step 4.
