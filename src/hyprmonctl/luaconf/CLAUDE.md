# luaconf/: Lua monitor file I/O

Tested in `tests/test_luaconf.py`. Fixture `tests/fixtures/user_monitors.lua` is a
snapshot of a real user file (string scale `"1.2"`, a comment header, `desc:` with
spaces).

| File | Role |
|---|---|
| `lexer.py` | Tokenizes any Lua 5.x: strings (quotes, long brackets, escapes), numbers (hex, exponents), all symbols, `--`/`--[[ ]]` comments. Raises `LuaSyntaxError(line)`. |
| `parser.py` | Extracts only **top-level** `hl.monitor({...})` / `hl.monitor{...}` calls into `MonitorRule`s. Nested tables become `LuaTable`; non-literal values become `LuaRaw(source)`. Any other top-level code is skipped by tracking bracket and block (`function/do/if/repeat` … `end/until`) depth, and its first line is recorded in `foreign_lines`. Calls nested in blocks count as foreign. `parse_source` never raises; errors land in `ParsedConfig.error`. `content_hash` gives the 16-hex `fileHash`. |
| `writer.py` | `render_file` (header comment, then rules), `render_rule` (multi-line, `=` aligned, 4-space indent; this matches hand-written files), `render_call` (single line, for `hyprctl eval`), `write_atomic` (temp file plus `os.replace`, copies mode, optional `<file>.bak`). |
| `discovery.py` | `require("a.b")` maps to `<hypr dir>/a/b.lua`. `default_lua_path` picks the first required module containing "monitor". `is_required` returns True, False, or None when `hyprland.lua` is unreadable. |

## Behavior to preserve

- **Round-tripping:** parsing the writer's output must give the same rules back
  (tested).
- **Floats** are written via `scale.format_scale` (max 6 decimals, `1.0` becomes `1`).
  Strings get double quotes with escapes. `LuaRaw` is written verbatim.
- **What a save loses:** comments and foreign code are not preserved, and the GUI
  warns about this through diagnostics. Don't silently widen what is dropped.
- **Writes are atomic.** Never write the target file in place.
