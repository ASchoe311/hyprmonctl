# Decisions and context log

Newest first. Each entry records what changed and why, so later agents don't undo it
or relearn it. Keep entries short, and link the code or file they concern. Current
state belongs in the module `CLAUDE.md` files; this log is for the reasons and history
behind it.

## 2026-10-22: Agent context system

**What:** A root `CLAUDE.md` plus per-module `CLAUDE.md` files, this log, `AGENTS.md`
(a pointer), skills in `.claude/skills/` (`hyprland-ipc`, `hyprland-lua-config`,
`hyprmonctl-verify`), and dev tools in `tools/` (`render_ui.py`, `backend.py`).
`CLAUDE.md` files are excluded from the wheel.

**Why:** The user asked that agents always record important context changes in
markdown for each other, with per-module files so an agent loads only what its task
needs.

## 2026-10-22: Revert restores a snapshot, not "defaults"

**What:** `preview()` snapshots the live monitors before the first preview.
`restore_rules(..., before)` re-declares the touched outputs using the file rule, with
geometry pinned to that snapshot. Monitors with no rule now start the draft with their
**live** scale.

**Why:** Hyprland gives a monitor with no matching rule scale 1, but `scale = "auto"`
gives headless outputs 2. Re-declaring "preferred/auto/auto" therefore changed the
screen on revert. Found while stress-testing with 5 headless outputs. Test:
`test_restore_rules_pin_to_state_before_preview`.

## 2026-10-22: Many-monitor fixes

- **Canvas framing:** `LayoutCanvas.refit()` read `zoom` back after assigning it, but
  `zoom` has a `Behavior`, so it got the in-flight value and mis-framed the layout. It
  now computes from a local value.
- **Tab bar:** `HTabBar` uses equal widths when the tabs fit, and natural widths with
  horizontal scrolling, edge fades and keep-selected-visible when they don't. Tabs
  carry the same number pill as the canvas tiles.
- **`duplicate-output`** is now shown on the identifier row.

## 2026-10-22: Qt log noise

**What:** `hyprmonctl install-desktop` writes `~/.local/share/applications/hyprmonctl.desktop`,
with `Exec` set to the absolute path of the running `hyprmonctl`. `gui/app.py` filters
`qt.qpa.services` and `qt.qpa.wayland.textinput` warnings.

**Why:**
- The portal warning was a missing desktop entry for app id `hyprmonctl`, and
  installing the entry fixes it. The filter just keeps runs without the entry quiet.
- The text-input warning is Qt-internal and harmless.
- Generating the entry, rather than shipping a static file, makes `Exec` correct for
  both `uv tool` installs and dev venvs.

## 2026-10-22: Short tiled windows

- **Dialogs:** `ModalDialog` scrolls its body and keeps the title and buttons pinned.
  The Settings buttons were cut off in a ~470 px tall tile.
- **Header:** the file chip's width is capped and elided, because a long path widened
  the whole page past the window.
- **Floating:** the app does not float by default; that's the user's preference.
  `README.md` offers an optional float rule.

## 2026-10-22: Drag behavior

- **Scroll stealing:** the tile `MouseArea` uses `preventStealing`. The page ScrollView
  was stealing vertical drags and cancelling them.
- **Pinning auto positions:** dragging pins every auto-positioned monitor at its
  displayed position (`MonitorStore.moveMonitor`). Hyprland recomputes `auto`
  positions when another monitor gets an explicit one; a laptop panel jumped to x=3520
  in a live test. Tiles show an `AUTO` badge so users understand this.

## 2026-10-22: Initial architecture

- **Python core and API:** a stdlib-only Python core, with a JSON-RPC 2.0 API as the
  single contract (the `rpc/` package).
  - The UI is QML that talks only through a duck-typed transport (`send` /
    `messageReceived`).
  - Hosts: PySide6 with an in-process transport for the standalone app, and the
    Quickshell adapter running `hyprmonctl serve` over stdio. The user required an
    independent app that is also easy to embed in Quickshell.
  - Rejected:
    - A Quickshell-only app: not independent.
    - A C++ QML plugin: compile and ABI friction.
    - A socket daemon: lifecycle complexity.
- **PySide6 from a uv venv** (`gui` extra), chosen by the user. Arch's `pyside6` (6.12)
  would have forced a full system upgrade, since system Qt was 6.11.
- **Apply flow (user choice):** a live preview via `hyprctl eval`, then a
  "Keep / Revert" countdown.
  - The revert timer runs in the **backend**, so a frozen UI still reverts. Closing the
    client also reverts.
  - Keep writes atomically with a `.bak`, then reloads, but only if `hyprland.lua`
    actually requires the file. Otherwise the reload would undo the layout.
  - Only changed monitors are eval'd, plus any touched by a pending earlier preview.
- **Identifier default (user choice):** `desc:` with serial, then the internal
  connector, then a unique `desc:`, then the connector.
- **Theme (user choice):** follows matugen `colors.json` (default: illogical-impulse's
  path), with a COSMIC-like dark fallback. The visual design is modeled on COSMIC
  Settings → Displays, at the user's request.
- **Lua file handling:** we parse only top-level `hl.monitor` calls and regenerate the
  whole file. We preserve rules for disconnected monitors, the fallback rule, and
  unknown fields/expressions (`extra`, `LuaRaw`). Comments and other code are dropped,
  with a diagnostic warning and a `.bak`. Simpler and more predictable than
  round-tripping arbitrary Lua.
