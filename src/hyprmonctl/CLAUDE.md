# src/hyprmonctl: package root

Files here glue the subpackages together. This file loads for any work under
`src/hyprmonctl`, so it is kept short; details live in each subpackage's `CLAUDE.md`.

| File | Role |
|---|---|
| `service.py` | `MonitorService`: every operation a client can do. Orchestrates `model/`, `luaconf/`, `hyprland/`, `settings`. |
| `settings.py` | `Settings` dataclass and `SettingsStore` (JSON at `~/.config/hyprmonctl/settings.json`). |
| `cli.py` | argparse entry point (`hyprmonctl …`); `build_service()` is the one place a real service is wired up. |
| `serialize.py` | `to_json`: dataclasses to camelCase JSON. It camel-cases **dict keys** too (so theme keys become `surfaceContainer`), so use lists rather than dicts keyed by user data. |
| `paths.py` | XDG paths, `expand` (`~`/`$VAR`), `contract` (back to `~/…`), `qml_dir()`. |
| `desktop.py` | Launcher entry (`hyprmonctl install-desktop`). `APP_ID = "hyprmonctl"` is also the Wayland app id the GUI sets. |

## `MonitorService` essentials

- **Dependency injection** for tests: `compositor` (anything matching
  `hyprland.ipc.Compositor`), `settings` store, `timer_factory`, `clock`, and
  `main_config` (path to `hyprland.lua`).
- **Threading:** each public method takes `self._lock` (RLock). Timers fire on other
  threads. Listeners (`subscribe`) are called with `(event, payload)` and must be
  thread-safe; RPC sessions serialize their writes.
- **`state()`** builds the `AppState` sent to clients. It re-reads the Lua file every
  time; nothing is cached, so the file on disk is the source of truth. `fileHash`
  guards later writes.
- **Preview lifecycle:**
  1. **First preview:** `preview(draft)` validates (any `error` issue raises
     `InvalidDraftError`). It then snapshots the live monitors into
     `_Preview.before`.
  2. **Apply:** it evals the rules for changed configs (`model.draft.changed_configs`)
     plus any monitor touched by an earlier, still-pending preview, all in one
     atomic eval.
  3. **Timer:** it starts `confirmTimeout` seconds.
  4. **End states:**
     - `confirm()` saves the pending draft.
     - `revert()`, the timer, a failed eval, or `close()` restore the snapshot via
       `model.draft.restore_rules(..., before)`.
- **`save(draft)`:**
  1. Checks the hash; raises `ConflictError` if the file changed on disk.
  2. `build_rules`, then `writer.write_atomic` (keeps a `.bak`).
  3. Runs `reload` **only if** `discovery.is_required(file) is not False`. Reloading
     when Hyprland doesn't load the file would wipe the live layout.
  4. Returns Hyprland's `configerrors`.
- **Events emitted:** `monitors.changed`, `preview.started`, `preview.reverted`
  (`reason`: user, timeout or closed), `config.saved`, `settings.changed`. These
  become RPC notifications.

## Settings

- **Precedence:** defaults, then the file, then per-process overrides (CLI
  `--lua-path`). `update()` validates each key and drops a matching override, so the
  user's explicit change wins.
- **Validation:** unknown or invalid keys raise `ValueError`. Bad entries already in
  the file are skipped silently, so a hand-broken file never stops the app.
- **`luaPath` default:** computed via `luaconf.discovery.default_lua_path()` when unset.

## Adding an API operation (checklist)

1. Add the method to `MonitorService`; put the pure logic in `model/`.
2. Map it in `rpc/dispatcher.py` (method table, docstring list, error mapping if it
   raises something new).
3. Add a test in `tests/test_service.py` and/or `tests/test_rpc.py`.
4. Call it from `qml/HyprMonCtl/MonitorStore.qml` if the UI needs it.
5. Update the API table in `README.md` and `rpc/CLAUDE.md`.
