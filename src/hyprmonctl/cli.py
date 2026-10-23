"""Command-line entry point: `hyprmonctl <command>`."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from hyprmonctl import __version__, paths
from hyprmonctl.hyprland.ipc import HyprlandError, HyprlandIPC
from hyprmonctl.serialize import camel, to_json
from hyprmonctl.service import MonitorService
from hyprmonctl.settings import SettingsStore


def build_service(lua_path: str | None = None) -> tuple[MonitorService, HyprlandIPC]:
    ipc = HyprlandIPC()
    store = SettingsStore(overrides={"luaPath": lua_path} if lua_path else None)
    return MonitorService(ipc, store), ipc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyprmonctl", description="Configure Hyprland monitors (Lua config).")
    parser.add_argument("--version", action="version", version=f"hyprmonctl {__version__}")
    parser.add_argument("--lua-path", help="monitor config file to use for this invocation (overrides settings)")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("gui", help="open the configuration window")
    serve = sub.add_parser("serve", help="run the JSON-RPC API server")
    serve.add_argument("--stdio", action="store_true", default=True, help="speak newline-delimited JSON-RPC on stdin/stdout (default)")
    status = sub.add_parser("status", help="show connected monitors and the rules that configure them")
    status.add_argument("--json", action="store_true", help="print the full state as JSON")
    sub.add_parser("render", help="print Lua that captures the current live layout")

    settings = sub.add_parser("settings", help="show or change settings")
    settings_sub = settings.add_subparsers(dest="action", metavar="ACTION")
    settings_sub.add_parser("get", help="print all settings as JSON")
    set_cmd = settings_sub.add_parser("set", help="change one setting, e.g. `settings set luaPath ~/.config/hypr/monitors.lua`")
    set_cmd.add_argument("key")
    set_cmd.add_argument("value", help="JSON value (bare strings are accepted)")

    sub.add_parser("qml-path", help="print the directory to add to QML_IMPORT_PATH for `import HyprMonCtl`")
    desktop = sub.add_parser("install-desktop", help="install the launcher entry in ~/.local/share/applications")
    desktop.add_argument("--print", action="store_true", help="print the entry instead of installing it")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = args.command or "gui"
    try:
        if command == "gui":
            from hyprmonctl.gui.app import run

            return run(lua_path=args.lua_path)
        if command == "qml-path":
            print(paths.qml_dir())
            return 0
        if command == "install-desktop":
            return _install_desktop(args.print)
        if command == "settings":
            return _settings(args)

        service, ipc = build_service(args.lua_path)
        if command == "serve":
            from hyprmonctl.rpc.stdio import serve_stdio

            return serve_stdio(service, ipc)
        if command == "status":
            return _status(service, args.json)
        if command == "render":
            sys.stdout.write(service.render_live())
            return 0
    except HyprlandError as exc:
        print(f"hyprmonctl: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"hyprmonctl: {exc}", file=sys.stderr)
        return 1
    return 1


def _install_desktop(print_only: bool) -> int:
    from hyprmonctl import desktop

    if print_only:
        sys.stdout.write(desktop.render_entry(desktop.launch_command()))
    else:
        print(f"Installed {paths.contract(desktop.install())}")
    return 0


def _settings(args: argparse.Namespace) -> int:
    store = SettingsStore(overrides={"luaPath": args.lua_path} if args.lua_path else None)
    if args.action == "set":
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        store.update({camel(args.key): value})
    print(json.dumps(to_json(store.load()), indent=2))
    return 0


def _status(service: MonitorService, as_json: bool) -> int:
    state = service.state()
    if as_json:
        print(json.dumps(to_json(state), indent=2))
        return 0
    print(f"Config file: {state.lua_path_display}{'' if state.file_exists else '  (not created yet)'}")
    for entry in state.monitors:
        live, config = entry.live, entry.config
        where = "disabled" if live.disabled else f"{live.width}x{live.height}@{live.refresh_rate:g} at {live.x},{live.y} scale {live.scale:g}"
        print(f"\n[{entry.id + 1}] {entry.name}" + (f"  {entry.description}" if entry.description else ""))
        print(f"    live:   {where}")
        source = "fallback rule" if entry.matched_by_fallback else ("rule #%d" % config.rule_index if config.rule_index is not None else "no rule (defaults)")
        print(f"    config: output={config.output!r} mode={config.mode} position={config.position} scale={config.scale}  [{source}]")
    if state.saved_rules:
        print("\nOther rules in the file:")
        for rule in state.saved_rules:
            print(f"    #{rule.index} {rule.output or '(fallback)'}  [{rule.status}]")
    for issue in state.diagnostics:
        print(f"\n{issue.severity}: {issue.message}")
    return 0
