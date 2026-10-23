# tests/

Run with `uv run pytest -q`. No running Hyprland, display or PySide6 is needed; the
GUI is verified separately (see the `hyprmonctl-verify` skill).

## Fixtures (`conftest.py`)

- **`fixtures/monitors.json`:** real `hyprctl monitors all -j` output.
  - `eDP-1`: laptop, 1920x1200, scale 1.2, no serial.
  - `DP-1`: `Dell Inc. DELL P2725QE FKYZQB4`, 1080p with duplicate modes.
  - Use the `monitors` fixture to get them as `MonitorInfo`s.
- **`fixtures/user_monitors.lua`:** a real user file, with a comment header,
  `scale = "1.2"` as a string, and a rule for a disconnected `desc:… S3422DWG …`.
  Available through the `user_lua` fixture.
- **`env` fixture:** a `MonitorService` wired to fakes:
  - `FakeCompositor` records `evals` and `reloads`; set `fail_eval` to simulate a
    rejected eval.
  - `FakeTimer` never fires on its own; call `.fire()`.
  - `FakeClock` has a settable `.now`.
  - The service writes to tmp files: `env.lua_path`, plus an `env.main_config` that
    `require`s it, and settings in `tmp_path`.
  - `env.events` collects emitted notifications.

## Files

| File | Covers |
|---|---|
| `test_luaconf.py` | lexer, parser (foreign code, raw values, nested calls), writer round-trip and style, atomic write, discovery |
| `test_model.py` | modes, identity matching and ranking, scale validity, geometry |
| `test_draft.py` | draft building, ownership, `build_rules` order, restore rules, validation codes |
| `test_service.py` | preview, timeout, revert, confirm, conflicts, reload skipping, settings |
| `test_rpc.py` | envelopes, error codes, stdio server |
| `test_desktop.py` | launcher entry |

## Conventions

- **Test behavior through the public functions.** When asserting the exact Lua sent
  to Hyprland, compare full `hl.monitor({...})` strings; those strings are the
  contract.
- **New Hyprland facts get a test with the observed values.** For example,
  `test_restore_rules_pin_to_state_before_preview` encodes "no-rule scale is 1, not
  auto".
