# model/: pure logic

No I/O, no Hyprland connection, no Qt: everything here is deterministic and unit-tested
(`tests/test_model.py`, `tests/test_draft.py`).

| File | Contents |
|---|---|
| `monitor.py` | `Mode` (parses `1920x1080`, `…@60`, hyprctl's `…@60.00Hz`; `str()` is `WxH@R.RR`). `MonitorInfo.from_hyprctl` de-duplicates `availableModes`, keeping driver order. `label` (`27.2" DP-1 external display` / `14.0" laptop display`). `resolutions()` groups modes. `resolve_special_mode` handles `preferred` (first listed), `highres`, `highrr` and `maxwidth`. |
| `rule.py` | `MonitorRule` (known fields plus `extra`; `None` means unspecified), `LuaRaw` (an expression kept verbatim), `LuaTable` (ordered entries), and value parsers (`parse_scale` accepts `"1.2"`, `parse_position`). `KNOWN_FIELDS` is also the order fields are written in. |
| `identity.py` | Hyprland's rule-to-monitor matching (`matches`, `resolve_rule`: last-defined wins, `desc:` is a prefix match, `""` is the fallback), identifier `candidates`, and `default_identifier` ranking. |
| `layout.py` | `Rect`, `logical_size` (scale, then odd transforms swap w/h), `find_overlaps`, `find_detached` (overlapping monitors are not also reported as detached). |
| `scale.py` | Valid scales are k/120 where w and h divide evenly. `valid_scales`, `is_valid_scale`, `nearest_valid_scale`, `nice_scales` (the 25% grid), `format_scale`. |
| `state.py` | Shapes exchanged with clients: `MonitorConfig`/`Draft` (with strict `from_json`), `MonitorEntry`, `SavedRule`, `Issue`, `AppState`, … |
| `draft.py` | Converting rules to drafts and back, preview/restore rules, and `validate`. |

## Key semantics (`draft.py`)

- **`initial_configs`** reproduces what the *file* says:
  - A monitor keeps the `output` of the rule that matches it.
  - A monitor matched only by the fallback rule, or that shares a rule another monitor
    owns, gets `default_identifier`. Its `rule_index` still points at the rule it
    derives from, so `extra` fields carry over.
  - A monitor with no rule uses `DEFAULT_RULE` (preferred, auto) **with its live
    scale**. Hyprland's no-rule scale is 1, not `"auto"`.
- **`build_rules`** writes, in this order: fallback rules, then the kept saved rules
  (file order, untouched objects), then one rule per connected monitor. Connected
  monitors come last so they win.
- **`config_to_rule`** copies `extra` from the base rule. It writes `transform` only if
  it's non-zero or the base had it. A disabled monitor keeps its other fields too.
- **`restore_rules(outputs, monitors, rules, before)`** re-declares every output name
  used during a preview: the file rule, with mode/position/scale/transform pinned to
  the `before` snapshot.
- **`validate`** returns `Issue`s and authoritative `placements`. Auto-positioned
  monitors use their live position.

## Issue codes are an API

The QML filters on these codes. Rename one only together with the QML that uses it
(grep `qml/` for the string).

| Code | Severity | Shown in QML |
|---|---|---|
| `empty-output`, `output-mismatch`, `duplicate-output` | error | IdentifierRow |
| `output-ambiguous` | warning | IdentifierRow |
| `invalid-scale` | error | ScaleRows |
| `mode-unavailable` | warning | ModeRows |
| `custom-mode` | info | ModeRows |
| `bad-mirror` | error | MonitorSettingsPanel |
| `overlap`, `all-disabled` | error | ArrangementCard |
| `detached` | warning | ArrangementCard |
| `not-connected` | warning | action bar count only |

File-level diagnostics (`file-missing`, `parse-error`, `foreign-code`, `raw-values`,
`not-loaded`, `hyprland-errors`) come from `service.py` and appear in
DiagnosticsBanner.

## Mirrored in JS

`qml/HyprMonCtl/Layout/Geometry.js` re-implements `effective_mode`, `effective_scale`,
`logical_size` and the auto-placement fallback, so dragging gets instant feedback.
**If you change one, change the other.** The backend stays authoritative for errors.

## Identifier ranking (user decision)

1. `desc:<description>` when the monitor reports a serial and that is unique.
2. The connector for built-in panels (`eDP`/`LVDS`/`DSI`).
3. `desc:<description>` when it is unique among connected monitors.
4. Otherwise the connector.

Headless outputs have an empty description, so they always get the connector.
