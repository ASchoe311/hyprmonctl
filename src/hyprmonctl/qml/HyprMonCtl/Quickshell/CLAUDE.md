# Quickshell/: optional adapter (Quickshell only)

The only place in the QML tree allowed to `import Quickshell` or `Quickshell.Io`.
Everything else must stay host-agnostic.

| File | Role |
|---|---|
| `ProcessTransport.qml` | Runs `command` (default `["hyprmonctl", "serve"]`) through `Quickshell.Io.Process` with `stdinEnabled`. `SplitParser` lines become `messageReceived`; `send(line)` becomes `process.write(line + "\n")`. `connected` mirrors `process.running`; `running` controls the process. stderr goes to `console.warn`. |
| `MonitorConfigWindow.qml` | A `FloatingWindow` (it tiles like a normal toplevel under Hyprland) containing the transport and a `MonitorConfigurator`. The backend runs only while the window is visible. The transport is passed only once `connected`, so the store's first `state.get` doesn't race process start-up. |

## Using it

- **Import path:** the user's shell adds the QML dir with
  `//@ pragma Env QML_IMPORT_PATH=<hyprmonctl qml-path>` in their `shell.qml`.
  Verified to work. Alternatively, set `QML_IMPORT_PATH` in the environment `qs`
  runs with.
- **`hyprmonctl` on PATH:** `ProcessTransport` needs it, or set `command` to an
  absolute path.
- **Example:** `examples/quickshell/shell.qml` shows `LazyLoader` plus `IpcHandler`
  (`qs ipc call displays toggle`).

## Testing

See the `hyprmonctl-verify` skill, step 6. The window class is `org.quickshell` and
the title is `Displays`. Quickshell's system Qt is 6.11, so shared QML must not use
APIs newer than that.
