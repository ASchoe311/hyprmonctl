---
name: hyprland-lua-config
description: Reference for Hyprland's Lua configuration (0.55+, the `hl.*` API) - how hyprland.lua loads modules with require(), every `hl.monitor` field and value format, how rules are matched to monitors (desc prefix, last rule wins, fallback), Hyprland's real defaults, window rules, binds and events, and where the official docs are. Use when reading or writing Hyprland Lua config, or when changing hyprmonctl's Lua parser/writer, identifier matching or validation.
---

# Hyprland Lua config

Since Hyprland 0.55 the config is Lua; hyprlang (`hyprland.conf`) is deprecated. The
0.54 wiki pages still describe the old syntax, so don't mix them up.

## Files and modules

- **Entry point:** `~/.config/hypr/hyprland.lua`.
- **Modules:** loaded with `require("a.b")`, which resolves to
  `~/.config/hypr/a/b.lua` (dots become slashes, relative to `~/.config/hypr`).
  A `require` inside `if is_file_exists(...) then … end` still counts.
- **hyprmonctl's target file:** found by scanning `require` strings for "monitor"
  (`luaconf/discovery.py`). It warns when the configured file isn't required, because
  then edits never take effect.

## `hl.monitor({...})`

`output` is required; every other field is optional.

| Field | Values | Default |
|---|---|---|
| `output` | Connector name (`DP-1`, `eDP-1`, `HEADLESS-2`), `desc:<description prefix>`, or `""` for the fallback rule | – |
| `mode` | `"WxH@Hz"` (e.g. `"1920x1080@144"`, fractional Hz fine), `"preferred"`, `"highres"`, `"highrr"`, `"maxwidth"`, or `"modeline …"` | preferred |
| `position` | `"XxY"` in logical pixels (negative allowed; Y is inverted, so negative means above), `"auto"`, `"auto-right/left/up/down"`, `"auto-center-right/left/up/down"` | auto |
| `scale` | Number, `"auto"`; a numeric string like `"1.2"` is accepted too | see Defaults |
| `transform` | 0–7: 0 normal, 1 90°, 2 180°, 3 270°, 4 flipped, 5–7 flipped plus 90/180/270 | 0 |
| `disabled` | `true` removes the monitor from the layout | false |
| `mirror` | Output name to mirror | – |
| `bitdepth` | 8 or 10 | 8 |
| `cm` | `auto`, `srgb`, `dcip3`, `dp3`, `adobe`, `wide`, `edid`, `hdr`, `hdredid` | srgb |
| `vrr` | 0 off, 1 on, 2 fullscreen only, 3 fullscreen with video/game content (same as `misc:vrr`) | 0 |
| `icc` | Absolute path to an ICC profile (overrides `cm`, forces `sdr_eotf = srgb`) | – |
| `sdr_eotf` | `default`, `gamma22`, `srgb` | default |
| `sdrbrightness`, `sdrsaturation` | Floats, SDR content inside HDR | 1.0 |
| `sdr_min_luminance`, `sdr_max_luminance`, `min_luminance`, `max_luminance`, `max_avg_luminance` | Numbers | – |
| `supports_wide_color`, `supports_hdr` | -1 off, 0 auto, 1 on | 0 |
| `reserved_area` | Integer, or `{ top =, right =, bottom =, left = }` | 0 |

hyprmonctl models `output` through `disabled` (the first ten rows). Any other field is
carried through untouched in `MonitorRule.extra`.

### Layout rules

- **Positions use the logical size:** the mode divided by the scale, with width and
  height swapped for transforms 1, 3, 5 and 7.
- **Monitors must not overlap.** They should share an edge, or the cursor can't cross
  between them.
- **The scale must give whole logical pixels** on the 1/120 grid. 1920x1200 at 1.2 is
  valid; at 1.4 it is not, and Hyprland picks the nearest valid scale and shows a
  warning.
- **Mirroring** shows the source unscaled; there is no re-render.

### Matching rules to monitors

These semantics are mirrored in `model/identity.py`; keep the two in sync.

- **`desc:X` matches by prefix:** the monitor's description (`"Make Model Serial"`) or
  `"Make Model"` must start with `X`.
- **A plain name must match exactly** (the connector name).
- **The last-defined matching rule wins.** A runtime rule with the same `output`
  replaces the earlier one.
- **`output = ""` is the fallback**, used only when nothing else matches.

### Defaults, as observed

- **No matching rule at all:** mode preferred, position auto, **scale 1**.
- **`scale = "auto"`** chooses from pixel density. That differs from 1 on hi-DPI
  panels, and on headless outputs (0 mm reported size), where it gives 2.
- **`auto` positions:** the first monitor goes at 0,0 and others go to the right. They
  are recomputed whenever another monitor changes.

## Other `hl.*` calls seen in real configs

```lua
hl.window_rule({ match = { class = "^(foo)$", title = "^(Open File)(.*)$" }, float = true, center = true, size = "900 900" })
hl.bind("SUPER + ALT + Space", hl.dsp.window.float({ action = "toggle" }), { description = "Window: Float/Tile" })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
hl.on("hyprland.start", function () hl.exec_cmd("qs -c ii") end)
hl.env("qsConfig", "ii")
```

Query functions also exist: `hl.get_monitors()`, `hl.get_active_monitor()`,
`hl.get_windows()`, `hl.get_config()` and others. They return userdata; see the
`hyprland-ipc` skill for how to introspect.

## Official docs

- Monitors: https://wiki.hypr.land/Configuring/Basics/Monitors/
- Everything else lives under https://wiki.hypr.land/Configuring/

The wiki pages are large (the Monitors page is about 290 KB). When using WebFetch,
the article body sits near the end: the first ~200,000 characters are navigation, so
fetch with `offset: 200000`.

## Keeping this current

When a new Hyprland version changes a field, a default or the matching behavior,
update this file, note the version, update `model/identity.py`, `model/draft.py` and
`luaconf/` to match, and add an entry to `docs/decisions.md`.
