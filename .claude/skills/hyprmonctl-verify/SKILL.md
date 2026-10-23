---
name: hyprmonctl-verify
description: How to verify changes to hyprmonctl end to end - unit tests, qmllint, offscreen UI screenshots with scripted clicks/drags/scrolls (tools/render_ui.py), live preview/revert checks against the running Hyprland through the JSON-RPC backend (tools/backend.py), many-monitor stress tests with headless outputs, the real window, and the Quickshell adapter. Use after changing Python, QML or API code in this repo, before reporting the work as done.
---

# Verifying hyprmonctl changes

Pick the steps that cover your change; UI changes need a screenshot you have looked
at. All commands run from the repo root. The GUI tools need the venv:
`uv sync --extra gui` (one time).

## 0. Ground rules

- Never point a test at the user's real monitors file when it might save. Copy it to
  a scratch dir and pass `--lua-path <copy>`:
  ```sh
  cp ~/.config/hypr/config/monitors.lua "$SCRATCH/monitors.lua"
  ```
  Use your session scratchpad, or `mktemp -d`. Reading the real file is fine.
- Never write `~/.config/hyprmonctl/settings.json` in tests. `tools/backend.py` isolates
  `XDG_CONFIG_HOME` for you.
- Anything that previews live changes the user's screen. Keep it short, make sure it
  reverts, and compare `Backend.live()` before and after.

## 1. Unit tests and lint (always)

```sh
uv run pytest -q
/usr/lib/qt6/bin/qmllint -I src/hyprmonctl/qml -I /usr/lib/qt6/qml \
  $(find src/hyprmonctl/qml/HyprMonCtl -name '*.qml' -not -path '*/Quickshell/*') src/hyprmonctl/qml/Main.qml
```

- **pytest:** needs no running Hyprland; see `tests/CLAUDE.md`.
- **qmllint:** one warning is known and harmless: `LayoutCanvas.qml … Cannot assign
  binding of type LayoutCanvas to LayoutCanvas`. It's a false positive from the
  circular type reference with `MonitorTile`. Anything else is new; fix it, or explain
  why not.

## 2. Offscreen UI screenshots (any QML change)

`tools/render_ui.py` loads the real UI with the real backend (live monitor state) on
Qt's offscreen platform. Nothing appears on screen, and the window size is exact. Run
steps in order, then view the PNG with the Read tool.

```sh
.venv/bin/python tools/render_ui.py "$SCRATCH/a.png" --size 789x900 --lua-path "$SCRATCH/monitors.lua"
.venv/bin/python tools/render_ui.py "$SCRATCH/b.png" --size 900x700 --lua-path "$SCRATCH/monitors.lua" \
  --js "store.select('DP-1'); store.setField('DP-1', 'scale', 1.25)" \
  --drag 578,318,120,360 \
  --js "console.log('POS', JSON.stringify(store.configs.map(c => c.name + '=' + c.position)))"
```

- **Scope inside `--js`:**
  - `cfg` is the MonitorConfigurator; `cfg.showLua()` and `cfg.showSettings()` open the dialogs.
  - `store` is the MonitorStore: `select`, `setField`, `moveMonitor`, `arrangeRow`,
    `removeSavedRule`, `discard`, `configs`, `issues`, `dirty` and the rest.
  - `win` is the window.
- **Showing the confirm dialog without touching Hyprland:**
  `store.previewTimeout = 15; store.previewDeadline = Date.now()/1000 + 11`.
- **Opening a dropdown:** find visible combo boxes, then open the nth popup:
  `function f(i,o){ if (i.options!==undefined && i.popup!==undefined && i.visible) o.push(i); for (const c of i.children) f(c,o); return o } f(cfg,[])[N].popup.open()`
- **Mouse steps:** `--drag x1,y1,x2,y2` and `--wheel x,y,deltaY` (negative scrolls
  down) take window coordinates. Find coordinates with a plain render first.
- **Window sizes to check:** a user's tiled window is often only ~780x470 or
  ~789x940, so test narrow and short sizes as well as roomy ones (900x1200).
- **Don't leave it applied:** `store.apply()` previews live. Only call it when you mean
  to, and with a scratch `--lua-path`; the tool reverts on exit.

## 3. Live backend checks (service, model, API or Hyprland changes)

`tools/backend.py` drives `hyprmonctl serve` with isolated settings:

```python
import sys; sys.path.insert(0, "tools")
from backend import Backend

with Backend(lua_path=scratch) as b:
    before = Backend.live()
    state = b.call("state.get")
    draft = Backend.draft(state)
    # Pin everything where it is, then change one thing (auto-placed monitors move otherwise).
    for c, m in zip(draft["monitors"], state["monitors"]):
        c["position"] = f'{m["live"]["x"]}x{m["live"]["y"]}'
    print(b.call("layout.validate", draft=draft)["issues"])  # must be [] before preview
    b.call("config.preview", draft=draft)
    print(Backend.live())                                      # the change is live
    b.call("config.revert")
    assert Backend.live() == before, "revert must restore exactly"
```

- **Safest real change:** a small move of a non-primary monitor, e.g. +80 px in y,
  still adjacent. Wait ~1 s before reading `live()`.
- **Timeout path:** `b.call("settings.update", patch={"confirmTimeout": 5})`, preview,
  then `b.wait_for("preview.reverted")`.
- **Saving:** only to the scratch file, with `reloadAfterSave` false unless the scratch
  file is the loaded one. It never is.

## 4. Many monitors (layout, canvas or tab changes)

```sh
for i in 1 2 3 4 5; do hyprctl output create headless; done
hyprctl monitors -j | python3 -c 'import json,sys; print([m["name"] for m in json.load(sys.stdin)])'
# … render (step 2) and live-check (step 3) …
for n in <the HEADLESS-N names>; do hyprctl output remove "$n"; done   # always clean up
```

Headless outputs have no description, a single mode, and 0 mm physical size, which
exercises the identifier fallbacks and empty-description paths. Details are in the
`hyprland-ipc` skill.

## 5. The real window (behavior that offscreen can't show)

```sh
(timeout 12 .venv/bin/hyprmonctl --lua-path "$SCRATCH/monitors.lua" gui &) ; sleep 4
python3 -I .claude/skills/hyprland-ipc/scripts/winshot.py hyprmonctl "$SCRATCH/win.png"
```

The window tiles like any app, so its size depends on the user's layout. Use `timeout`
so it never lingers.

## 6. Quickshell adapter (changes under `qml/HyprMonCtl/Quickshell/` or the transport contract)

```sh
(PATH="$PWD/.venv/bin:$PATH" QML_IMPORT_PATH="$(.venv/bin/hyprmonctl qml-path)" \
  timeout 12 qs -p examples/quickshell/shell.qml > "$SCRATCH/qs.log" 2>&1 &) ; sleep 5
python3 -I .claude/skills/hyprland-ipc/scripts/winshot.py org.quickshell "$SCRATCH/qs.png" --title '^Displays$'
grep -iv info "$SCRATCH/qs.log"
```

Success looks like the page loading with the shell's theme. "Not connected to the
hyprmonctl backend" means the transport handshake broke (see
`qml/HyprMonCtl/Quickshell/CLAUDE.md`).

## 7. Before you say "done"

- Tests pass, and qmllint shows nothing new.
- For UI work: you looked at the screenshots, including a narrow or short window.
- Anything you created is gone: headless outputs, runtime window rules (cleared with
  `hyprctl reload config-only`), stray processes (`pgrep -af 'hyprmonctl|qs -p'`).
  Don't kill a hyprmonctl the user started themselves.
- Important context changes are written down: in the module `CLAUDE.md` and
  `docs/decisions.md` (see the root `CLAUDE.md`).
