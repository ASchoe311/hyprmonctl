# rpc/: the JSON-RPC API

This is the single contract between the backend and every frontend: the bundled QML,
the Quickshell adapter and third-party scripts. **Treat changes as API changes:**
update `README.md` (API section) and bump `API_VERSION` in `__init__.py` for breaking
ones.

| File | Role |
|---|---|
| `dispatcher.py` | Method table, JSON-RPC 2.0 envelopes, exception-to-error-code mapping. `to_json` makes all results camelCase. |
| `session.py` | `RpcSession(service, send, ipc)` is one client: it dispatches lines, forwards service events as notifications (serialized by a send lock), runs a `MonitorEventListener` when `ipc` is given, and `close()` reverts any pending preview. |
| `stdio.py` | `serve_stdio`: newline-delimited JSON on stdin/stdout, handled sequentially. Exits on EOF (Quickshell stops the process, which reverts). |

## Methods

| Method | Params |
|---|---|
| `api.version` | – |
| `state.get` | – |
| `layout.validate` | `{draft}` |
| `config.render` | `{draft}` |
| `config.preview` | `{draft}` |
| `config.confirm` | – |
| `config.revert` | – |
| `config.save` | `{draft}` |
| `settings.get` | – |
| `settings.update` | `{patch}` |
| `theme.get` | – |

The draft shape is `{monitors: MonitorConfig[], keepRules: int[], fileHash}`; see
`model/state.py` (`Draft.from_json` validates it strictly).

## Error codes

| Code | Meaning |
|---|---|
| -32700 | parse |
| -32600 | invalid request |
| -32601 | unknown method |
| -32602 | invalid params (`ValueError`/`TypeError`/`KeyError`) |
| -32603 | internal |
| -32000 | Hyprland unavailable |
| -32001 | Hyprland rejected the request |
| -32002 | file changed on disk |
| -32003 | invalid draft; `data` holds the issues |
| -32004 | no preview to confirm |

## Notifications

`monitors.changed`, `preview.started`, `preview.reverted`, `config.saved`,
`settings.changed`.

## Transports

- **In-process (PySide6):** `gui/transport.py` runs one `RpcSession` per window, with
  requests on a single worker thread.
- **stdio:** `hyprmonctl serve` is used by `qml/HyprMonCtl/Quickshell/ProcessTransport.qml`
  and `tools/backend.py`.
- **QML side:** `qml/HyprMonCtl/RpcClient.qml` matches responses by `id` and turns
  messages without an id into `notification(method, params)`.
