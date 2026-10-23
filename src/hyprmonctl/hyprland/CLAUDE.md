# hyprland/: talking to the running compositor

For hyprctl usage, Lua eval and live-session safety, see the
`.claude/skills/hyprland-ipc` skill.

| File | Role |
|---|---|
| `ipc.py` | `HyprlandIPC` speaks the command socket directly (no `hyprctl` subprocess): `request`, `request_json` (`j/` prefix), `monitors()` (`j/monitors all`), `eval(code)` (raises `HyprlandError` unless the reply is `ok`), `reload()`, `config_errors()`. `Compositor` is the Protocol the service depends on; tests use `tests/conftest.FakeCompositor`. |
| `events.py` | `MonitorEventListener` is a daemon thread on `.socket2.sock`. It debounces `monitoradded[v2]`, `monitorremoved[v2]` and `configreloaded` into `on_change(event)`, and reconnects every 2 s if the socket drops. |

## Notes

- **Errors:** `HyprlandUnavailable` (no instance or socket) subclasses
  `HyprlandError`. The RPC layer maps them to codes -32000 and -32001.
- **Socket path:**
  `$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket.sock`. A missing
  signature raises `HyprlandUnavailable` when the request is made.
- **One listener per session:** each `rpc.session.RpcSession` starts its own listener.
  If you ever share a service across sessions, move the listener up to avoid duplicate
  notifications.
- **Batching:** `eval` accepts multiple statements, so the service batches all rules
  for one preview into a single call.
