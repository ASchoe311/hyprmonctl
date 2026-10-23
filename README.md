# hyprmonctl

A display settings app for Hyprland's Lua config (Hyprland 0.55+), styled after
COSMIC's Displays page. Drag monitors into place, pick modes, scales and rotation,
and choose how each monitor is identified. The result is written to a Lua file of
`hl.monitor({...})` rules.

It runs as a standalone app. The same UI is also a QML module you can embed in a
Quickshell config.

## Features

- **Arrangement canvas.** Drag monitors to place them; they snap to the edges and
  centers of other monitors. When dropped, a monitor attaches to the nearest free
  edge, so the cursor can always cross between displays.
- **Per-monitor settings.**
  - Resolution and refresh rate come from the modes the display advertises
    (`hyprctl monitors all`).
  - Scale lists only values Hyprland accepts for the current mode: the logical size
    must be whole pixels. A coarse dropdown and a fine stepper are provided.
  - Also: orientation (transform 0–7), mirroring, position (manual or Hyprland's
    `auto-*` placements), VRR, bit depth and color management preset.
- **Monitor identifier.** Each rule's `output` defaults to the most specific stable
  descriptor:
  1. `desc:Make Model Serial` when the monitor reports a serial.
  2. The connector name for built-in panels (`eDP-1`).
  3. `desc:Make Model` when that is unique among connected monitors.
  4. Otherwise the connector name.

  You can pick another candidate or type your own. Each choice shows whether it
  matches only this monitor.
- **Safe apply.**
  1. Apply turns the new layout on live with `hyprctl eval`.
  2. A countdown asks you to keep it. If you don't confirm within 15 s (configurable),
     the previous settings are restored. The timer runs in the backend, so it still
     fires if the window freezes or your screen goes blank.
  3. Keep writes the Lua file atomically, saves the old file as a `.bak`, and reloads
     Hyprland.
- **Preserves what it doesn't manage.**
  - Rules for monitors that aren't connected (other desks, docks) are listed and kept
    as they are, unless you remove them.
  - The fallback rule (`output = ""`) is kept the same way.
  - Fields the UI doesn't edit (`reserved_area`, `icc`, `sdr_*`, …) are carried over.
- **Diagnostics.** The app warns when the file has code it can't parse, or when
  Hyprland doesn't actually `require` the file. It also shows Hyprland's config errors
  after a save.
- **Follows your shell theme.** It reads a matugen-style `colors.json`, defaulting to
  illogical-impulse's. Without one it uses a COSMIC-like dark theme.

## Install

You need Python 3.11+ and Hyprland 0.55+ with a Lua config.

```sh
uv tool install '.[gui]'        # puts `hyprmonctl` in ~/.local/bin
# or, without the GUI (CLI + API only):
uv tool install .
```

Run `hyprmonctl install-desktop` to add a "Displays" launcher entry. It also lets
the desktop portal recognize the app's window.

The window opens tiled like any other app. Its app id is `hyprmonctl`, so if you'd
rather have it float, add a rule such as:

```lua
hl.window_rule({ match = { class = "^hyprmonctl$" }, float = true, size = "900 900", center = true })
```

## Usage

```sh
hyprmonctl                       # open the window (same as `hyprmonctl gui`)
hyprmonctl status                # connected monitors and the rule that configures each
hyprmonctl render                # print Lua capturing the current live layout
hyprmonctl install-desktop       # add the launcher entry (~/.local/share/applications)
hyprmonctl settings get
hyprmonctl settings set luaPath ~/.config/hypr/config/monitors.lua
hyprmonctl --lua-path /tmp/test.lua gui   # use another file for this run only
```

**Which file is written.** This is the `luaPath` setting. On first run hyprmonctl
looks at `require(...)` calls in `~/.config/hypr/hyprland.lua` and picks the first
module with "monitor" in its name, falling back to `~/.config/hypr/monitors.lua`.
Hyprland must load that file, for example:

```lua
require("config.monitors")   -- ~/.config/hypr/config/monitors.lua
```

Settings live in `~/.config/hyprmonctl/settings.json`:

| Key | Default | Meaning |
|---|---|---|
| `luaPath` | discovered | Monitor config file to write |
| `confirmTimeout` | `15` | Seconds before an unconfirmed preview reverts |
| `reloadAfterSave` | `true` | Run `hyprctl reload` after writing. Skipped if Hyprland doesn't load the file, because reloading would undo the applied layout. |
| `backup` | `true` | Keep `<file>.bak` |
| `themeColorsPath` | ii's `colors.json` | matugen-style palette; empty for the built-in theme |
| `snapDistance` | `16` | Snap distance in screen pixels while dragging |

## Quickshell integration

The UI is a set of QML modules that don't depend on Quickshell. A small adapter
module, `HyprMonCtl.Quickshell`, runs the backend as a child process
(`hyprmonctl serve`) and connects the two. To use it:

1. Add the modules to your config's import path. Put this in your `shell.qml`; the
   path comes from `hyprmonctl qml-path`:

   ```qml
   //@ pragma Env QML_IMPORT_PATH=/path/printed/by/hyprmonctl-qml-path
   ```

2. Open the window on demand:

   ```qml
   import Quickshell
   import Quickshell.Io
   import HyprMonCtl.Quickshell

   ShellRoot {
       LazyLoader {
           id: displays
           MonitorConfigWindow {
               visible: true
               onVisibleChanged: if (!visible) displays.active = false
           }
       }
       IpcHandler {
           target: "displays"
           function toggle(): void { displays.active = !displays.active; }
       }
   }
   ```

   Bind a key to `qs -c <config> ipc call displays toggle`. `examples/quickshell/shell.qml`
   is a runnable version:

   ```sh
   QML_IMPORT_PATH="$(hyprmonctl qml-path)" qs -p examples/quickshell/shell.qml
   ```

3. Embed it in your own panel instead, if you prefer:

   ```qml
   import HyprMonCtl
   import HyprMonCtl.Quickshell

   ProcessTransport { id: backend }
   MonitorConfigurator {
       transport: backend.connected ? backend : null
       showHeader: false
       followShellTheme: false   // keep your shell's palette
   }
   ```

   To restyle it, set properties on the `HyprMonCtl.Style` `Theme` singleton, or call
   `Theme.applyPalette({ primary: "#…", surfaceContainer: "#…", onSurface: "#…" })`.

If you'd rather build your own UI, talk to the API directly. It is the same JSON-RPC
the bundled UI uses.

## API

`hyprmonctl serve` speaks JSON-RPC 2.0 on stdin/stdout, one JSON object per line.
Requests are handled in order. Notifications can arrive at any time.

| Method | Params | Result |
|---|---|---|
| `api.version` | – | `{version, apiVersion}` |
| `state.get` | – | Monitors (live state, modes, valid scales, identifier candidates, current config), saved rules, diagnostics, settings, `fileHash` |
| `layout.validate` | `{draft}` | `{issues, placements}` |
| `config.render` | `{draft}` | `{lua}` |
| `config.preview` | `{draft}` | `{deadline, timeout}`: applies live, reverts unless confirmed |
| `config.confirm` | – | `{path, backupPath, fileHash, configErrors}`: keeps and saves the preview |
| `config.revert` | – | `{reverted}` |
| `config.save` | `{draft}` | Same as `config.confirm`, without a preview |
| `settings.get` | – | Settings |
| `settings.update` | `{patch}` | Settings |
| `theme.get` | – | `{colors}` |

Notifications:

- `monitors.changed`: hotplug or config reload
- `preview.started`
- `preview.reverted` (`reason`: `user`, `timeout` or `closed`)
- `config.saved`
- `settings.changed`

A draft is the `config` of each monitor from `state.get` (edited), plus the saved
rules to keep:

```json
{
  "monitors": [
    { "name": "DP-1", "output": "desc:Dell Inc. DELL P2725QE ABC123", "enabled": true,
      "mode": "2560x1440@100.00", "position": "-2560x0", "scale": 1.25, "transform": 0,
      "mirror": null, "bitdepth": null, "vrr": null, "cm": null, "ruleIndex": null }
  ],
  "keepRules": [1],
  "fileHash": "9f745616c9193f8c"
}
```

Passing `fileHash` from `state.get` makes writes fail with code `-32002` if the file
changed on disk in the meantime. Other errors use these codes:

| Code | Meaning |
|---|---|
| `-32000` | Hyprland not reachable |
| `-32001` | Hyprland rejected the request |
| `-32003` | Invalid draft; `data` lists the issues |
| `-32004` | No preview to confirm |

## How it works

```
src/hyprmonctl/
  model/        Pure logic, no I/O
    monitor.py    live monitor state from `hyprctl monitors all`, mode parsing
    rule.py       an hl.monitor rule (unknown fields kept in `extra`)
    identity.py   how `output` selects a monitor; identifier candidates and ranking
    layout.py     logical sizes, overlap and adjacency
    scale.py      valid fractional scales (1/120 grid, whole logical pixels)
    draft.py      file rules <-> editable drafts, preview/restore rules, validation
    state.py      data shapes exchanged with clients
  luaconf/      Lua tokenizer, parser (hl.monitor calls only), writer, require() discovery
  hyprland/     Command socket (monitors, eval, reload, configerrors) and event socket
  service.py    Orchestration: state, preview + revert timer, save, settings, theme
  rpc/          JSON-RPC dispatcher, per-client session, stdio server
  gui/          PySide6 host and in-process transport
  qml/
    Main.qml      standalone window
    HyprMonCtl/   MonitorConfigurator, MonitorStore (client state), RpcClient
      Style/        Theme singleton
      Controls/     styled primitives (rows, dropdowns, switches, dialogs, icons)
      Layout/       arrangement canvas, tiles, geometry and snapping (JS)
      Panels/       settings rows and cards
      Dialogs/      confirm countdown, Lua preview, settings
      Quickshell/   ProcessTransport + MonitorConfigWindow (Quickshell only)
```

Every frontend goes through the same JSON-RPC methods. The QML module depends only on
a *transport*: any object with `send(line)` and a `messageReceived(line)` signal. The
PySide6 host provides one that runs in-process; the Quickshell adapter provides one
that spawns `hyprmonctl serve`.

**Previews.** A preview evaluates `hl.monitor` calls only for the monitors you changed.
To revert, it re-declares each changed output using the file's rule for it, with mode,
position, scale and transform pinned to a snapshot of the screen taken before the
preview. That snapshot matters because Hyprland's implicit defaults don't reproduce the
screen reliably: a monitor with no rule gets scale 1, but `scale = "auto"` can choose
something else.

**Auto positions.** A monitor whose position is `auto` is placed by Hyprland and can
move when the others change. Such monitors carry an `AUTO` badge on the canvas.
Dragging any monitor pins all of them where they're shown, so what you see is what
gets applied.

**Limitations.**

- Comments in the monitors file are not preserved.
- Top-level code other than `hl.monitor(...)` calls is reported, then dropped on save.
  A backup is kept.
- Values written as Lua expressions are replaced with plain values when that
  monitor's rule is rewritten.

## Development

```sh
uv sync --extra gui
uv run pytest
uv run hyprmonctl --lua-path /tmp/scratch.lua gui     # try it without touching your config
/usr/lib/qt6/bin/qmllint -I src/hyprmonctl/qml $(find src/hyprmonctl/qml -name '*.qml')
```

The tests use a captured `hyprctl monitors all -j` and a fake compositor
(`tests/conftest.py`), so they don't need a running Hyprland.
