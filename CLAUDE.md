# hyprmonctl: agent guide

A display-settings app for Hyprland's **Lua** config (Hyprland 0.55+), styled after
COSMIC's Displays page. Users drag monitors on a canvas and choose mode, scale,
rotation and how each monitor is identified. The app writes `hl.monitor({...})` rules
to a Lua file the user designates (default: the `require`d module in
`~/.config/hypr/hyprland.lua` whose name contains "monitor").

It must work **standalone** (PySide6 window) and stay **easy to embed in
Quickshell** (a QML module plus an adapter). User-facing docs are in `README.md`.

## Keep context current (required)

Agents work on this repo one after another, so write down what the next one needs:

1. **When you change something another agent would need to know** (architecture,
   contracts between modules, invariants, file locations, non-obvious behavior,
   gotchas you hit, Hyprland facts you verified), update the `CLAUDE.md` nearest to
   that code in the same change. Edit it to describe the current state; don't append
   history.
2. **For decisions and discoveries with a "why"**, add a dated entry at the top of
   `docs/decisions.md`, e.g. a design choice, a rejected alternative, or a bug whose
   cause wasn't obvious.
3. **If you add a module or directory**, give it a `CLAUDE.md` and list it in the map
   below.
4. **If you learn new Hyprland behavior**, update the relevant skill in
   `.claude/skills/`.
5. Keep these files short and factual. Delete statements that stop being true.

## Context map: read only what your task touches

| Read | When working on |
|---|---|
| `src/hyprmonctl/CLAUDE.md` | service, settings, CLI, serialization (package root) |
| `src/hyprmonctl/model/CLAUDE.md` | rules, identity matching, validation, geometry, scale math |
| `src/hyprmonctl/luaconf/CLAUDE.md` | reading/writing the Lua file, `require` discovery |
| `src/hyprmonctl/hyprland/CLAUDE.md` | Hyprland IPC client, event listener |
| `src/hyprmonctl/rpc/CLAUDE.md` | JSON-RPC API (methods, errors, notifications, sessions) |
| `src/hyprmonctl/gui/CLAUDE.md` | PySide6 host, in-process transport |
| `src/hyprmonctl/qml/CLAUDE.md` | any QML: module layout, store, conventions, **QML gotchas** |
| `src/hyprmonctl/qml/HyprMonCtl/Layout/CLAUDE.md` | arrangement canvas, drag, snapping |
| `src/hyprmonctl/qml/HyprMonCtl/Quickshell/CLAUDE.md` | Quickshell adapter |
| `tests/CLAUDE.md` | fixtures, fakes, writing tests |
| `docs/decisions.md` | why things are the way they are (dated log) |

Skills in `.claude/skills/`:

- `hyprland-ipc`: hyprctl, sockets, Lua eval, headless monitors, screenshots, and
  live-session safety.
- `hyprland-lua-config`: `hl.monitor` fields and rule-matching semantics.
- `hyprmonctl-verify`: how to test changes end to end, including offscreen UI
  screenshots and live preview checks.

## Architecture

```
model/ (pure logic) ─┐
luaconf/ (Lua I/O)  ─┼─► service.py ─► rpc/ (JSON-RPC) ─┬─► gui/ (PySide6, in-process transport) ─┐
hyprland/ (IPC)     ─┘   (orchestration,                 └─► `hyprmonctl serve` (stdio) ──────────────┤
settings.py              revert timer)                         ▲ used by Quickshell adapter, scripts  │
                                                                                                       ▼
                                                 qml/HyprMonCtl (UI; talks JSON-RPC through a "transport")
```

- **One contract.** Every frontend speaks the JSON-RPC methods in `rpc/dispatcher.py`.
  The QML never calls Python directly; it only needs a transport with `send(line)`
  and a `messageReceived(line)` signal.
- **Python core is stdlib-only** (3.11+). PySide6 is only in the optional `gui` extra.
- **The backend owns safety.** A live preview reverts on a backend timer, and also
  when the client disconnects, so a frozen or blank-screened UI can't strand the
  user.

## Hard rules

- **Never modify the user's real Hyprland config or hyprmonctl settings while testing.**
  Use a scratch copy with `--lua-path` and `tools/backend.py` (isolated
  `XDG_CONFIG_HOME`). Reading is fine.
- **Live changes must be revertible and reverted.** Clean up headless monitors and
  runtime window rules you create (`hyprctl reload config-only` clears runtime rules
  without touching monitors). Don't kill processes the user started.
- **Preserve what the app doesn't manage.** That covers rules for disconnected
  monitors, the fallback rule, and unknown fields (`MonitorRule.extra`, `LuaRaw`).
  Writes are atomic and keep a `.bak`.
- **Revert restores the pre-preview screen snapshot**, not Hyprland "defaults" (see
  `docs/decisions.md`).
- **Shared QML must not import Quickshell.** Only `qml/HyprMonCtl/Quickshell/` may.
- **Validation issue `code`s are an API.** The QML filters on them; see
  `model/CLAUDE.md`.

## Commands

```sh
uv sync --extra gui                 # venv with PySide6 (.venv)
uv run pytest -q                    # unit tests, no Hyprland needed
uv run hyprmonctl --lua-path /tmp/x.lua gui     # run against a scratch file
uv run hyprmonctl status            # read-only summary of monitors and rules
.venv/bin/python tools/render_ui.py out.png --size 900x1000 --js "..."   # offscreen screenshot
/usr/lib/qt6/bin/qmllint -I src/hyprmonctl/qml -I /usr/lib/qt6/qml <files>
```

## Conventions

- **Match the surrounding code:** naming, comment density, idioms. Modules are small
  and single-purpose; put new logic where its peers live (pure logic goes in
  `model/`, not `service.py`).
- **Python:** dataclasses, type hints, `from __future__ import annotations`.
  Snake_case internally; JSON is camelCase via `serialize.to_json`, which also
  camel-cases **dict keys**.
- **QML:** design tokens come only from the `Theme` singleton; reuse
  `HyprMonCtl.Controls` primitives; use `pragma ComponentBehavior: Bound` in files
  with delegates. Must run on both PySide6's Qt (6.12) and the system Qt used by
  Quickshell (6.11), so avoid APIs newer than about Qt 6.7.
- **Every behavior change gets a test.** UI changes get an offscreen screenshot you
  have actually looked at.
- **Don't commit** unless the user asks.

## Environment (dev machine, 2026-10)

- Hyprland 0.56.2 with a Lua config.
- System Python 3.14; the project venv is Python 3.12 with PySide6-Essentials 6.12.
- System Qt 6.11. Quickshell 0.2.1 runs the user's shell (illogical-impulse, `qs -c ii`).
- The default theme colors path (`~/.local/state/quickshell/user/generated/colors.json`)
  is illogical-impulse's matugen output.
- `.qmlls.ini` (gitignored, absolute paths) gives the QML language server the import
  paths. Recreate it with `importPaths="<repo>/src/hyprmonctl/qml:/usr/lib/qt6/qml"`.
