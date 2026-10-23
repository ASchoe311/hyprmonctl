---
name: hyprland-ipc
description: How to query and control the running Hyprland (0.55+, Lua config) from a shell or Python - hyprctl commands, the raw IPC sockets, Lua eval/repl, dispatchers, runtime window rules, headless test monitors, the event socket and window screenshots - plus the safety rules for touching the user's live desktop. Use before running any hyprctl command or writing code that talks to Hyprland.
---

# Hyprland IPC

Facts here were verified on Hyprland 0.56.2 with a Lua config. Re-verify anything
marked *unverified* before relying on it, and add what you learn (see "Keeping this
current").

## Safety: this is the user's live desktop

- **Read-only is always fine:** `hyprctl monitors all -j`, `clients -j`,
  `workspaces -j`, `getoption <opt>`, `configerrors`, `version`, and pure queries via
  `repl 'return …'`.
- **Anything that changes state** (`eval` of `hl.monitor`/`hl.window_rule`,
  `dispatch`, `output create/remove`, `reload`) changes the user's screen. Only do it
  when the task needs it, keep it reversible, put things back, and tell the user
  exactly what you changed.
- **Never edit files under `~/.config/hypr`** (including the monitors file hyprmonctl
  manages) to test something. Copy the file to a scratch dir and use `--lua-path`.
- **Runtime changes last until the next reload.** `hyprctl reload config-only`
  re-reads the config *without* re-applying monitor rules: no flicker, and it drops
  every runtime rule you added. A plain `hyprctl reload` also re-applies monitors.
- **Monitor changes:** prefer hyprmonctl's backend preview, which auto-reverts (see
  the `hyprmonctl-verify` skill). If you `eval` monitor rules directly, save
  `hyprctl monitors -j` first and restore those exact values. Re-declaring "defaults"
  is not a restore (see Gotchas).

## Sockets and protocol

| Socket | Path |
|---|---|
| Commands | `$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket.sock` |
| Events | `.../.socket2.sock` |

On the command socket: connect, send the command string (what you'd pass to
`hyprctl`), read until EOF. Prefix the command with `j/` for JSON, e.g.
`j/monitors all`. In this repo `hyprmonctl.hyprland.ipc.HyprlandIPC` implements this
in Python; use it rather than shelling out from product code.

## Commands

| Purpose | Command | Notes |
|---|---|---|
| All monitors incl. disabled | `hyprctl monitors all -j` | `availableModes` like `"1920x1080@100.00Hz"`, which can contain duplicates. `mirrorOf` is `"none"` when not mirroring. |
| Windows | `hyprctl clients -j` | `class`, `title`, `at` [x,y], `size` [w,h], `floating` |
| Config errors | `hyprctl configerrors` / `j/configerrors` | JSON is `[""]` when there are none |
| Option value | `hyprctl getoption misc:vrr` | |
| Run Lua | `hyprctl eval '<lua>'` | Prints `ok`, or `error: <msg>` with exit code 7 |
| Lua REPL / query | `hyprctl repl '<lua>'` | Prints the returned value |
| Reload config | `hyprctl reload [config-only]` | |
| Virtual monitor | `hyprctl output create headless` / `output remove <NAME>` | See Monitors |
| Log | `hyprctl rollinglog [-f]` | |

## Lua through IPC

- **`eval` statement handling.** `eval` first tries the code as `return <code>;`.
  Several statements (separated by `;` or newlines) work in one call, so you can
  apply several `hl.monitor` rules in a single, atomic eval.
- **`repl` return values.** `repl` stringifies what you return. Objects come back as
  userdata, e.g. `HL.Monitor(0:eDP-1)`, which can't be iterated with `pairs`. Use the
  `j/` JSON commands for structured data.
- **Discover the API:**
  ```sh
  hyprctl repl 'local t={} for k,v in pairs(hl) do t[#t+1]=k..":"..type(v) end table.sort(t) return table.concat(t, "\n")'
  ```
  Swap `hl` for `hl.dsp` or `hl.dsp.window` to list dispatchers.
- **Dispatch:**
  ```sh
  hyprctl eval 'hl.dispatch(hl.dsp.no_op())'
  ```
  This pattern is verified. Dispatcher constructors seen in configs include
  `hl.dsp.window.float({ action = "toggle" })`,
  `hl.dsp.window.resize({ x = 640, y = 480, "exact" })` and
  `hl.dsp.exec_cmd("…")`. The legacy `hyprctl dispatch <name> <args>` still exists;
  its argument format is *unverified* in 0.56.
- **Runtime window rule** (for example to float a test window at a fixed size). It
  lasts until reload; clear it with `hyprctl reload config-only`.
  ```sh
  hyprctl eval 'hl.window_rule({ match = { class = "^hyprmonctl$" }, float = true, size = "900 1000", center = true })'
  ```

## Monitors

- **Live state:** `hyprctl monitors all -j`. Positions are in logical pixels (mode
  divided by scale, rotated by transform).
- **Test monitors:** `hyprctl output create headless` adds `HEADLESS-N`.
  - N keeps counting up within a session; numbers are not reused.
  - Each one is 1920x1080@60 with a single mode and scale 1.
  - `description`, `make`, `model` and `serial` are all empty, and
    `physicalWidth/Height` is 0.
  - They are placed automatically to the right of the others.
  - Remove them with `hyprctl output remove HEADLESS-N` when you're done. They take
    workspaces, and the cursor can wander onto them.
- **Gotchas (all observed):**
  - **No rule is not `scale = "auto"`.** A monitor with no matching rule gets scale 1.
    `"auto"` picks by pixel density, and headless outputs get 2. To undo a change,
    restore the recorded live values rather than re-declaring "defaults".
  - **`auto` positions get recomputed.** Giving one monitor an explicit position can
    move every `auto`-placed one. In testing, the laptop panel jumped to x=3520.
  - **Rule matching:** an eval'd rule with the same `output` replaces the earlier one,
    and the last-defined matching rule wins. `desc:` matches by description prefix.

## Events

```sh
socat -u UNIX-CONNECT:$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock -
```

Each line is `event>>data`. Monitor-related events:

- `monitoradded` / `monitoraddedv2`
- `monitorremoved` / `monitorremovedv2`
- `configreloaded`

`activewindow`/`activewindowv2` and others stream constantly.

## Screenshots of a window

```sh
python3 -I .claude/skills/hyprland-ipc/scripts/winshot.py hyprmonctl /tmp/shot.png
python3 -I .claude/skills/hyprland-ipc/scripts/winshot.py org.quickshell /tmp/qs.png --title '^Displays$'
```

Then view the PNG with the Read tool.

- **Pixel scale:** geometry is logical, the image is physical pixels.
- **Size:** a tiled window gets whatever its tile is. For a predictable size, add a
  temporary float rule (above) and clear it afterwards with `reload config-only`.
- **Prefer offscreen renders for hyprmonctl's own UI:** the offscreen renderer in the
  `hyprmonctl-verify` skill shows nothing on the user's screen, and its window size is
  exact.
- **Window classes:** Quickshell windows have class `org.quickshell`; hyprmonctl's
  standalone window has `hyprmonctl`.

## Keeping this current

If you discover new Hyprland behavior (a command's output format, a default, a
gotcha), add it here with the Hyprland version you saw it on. If it changed a design
decision, also add an entry to `docs/decisions.md`.
