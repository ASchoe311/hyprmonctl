"""Newline-delimited JSON-RPC over stdin/stdout (`hyprmonctl serve --stdio`)."""

from __future__ import annotations

import sys
from typing import TextIO

from hyprmonctl.hyprland.ipc import HyprlandIPC
from hyprmonctl.rpc.session import RpcSession
from hyprmonctl.service import MonitorService


def serve_stdio(service: MonitorService, ipc: HyprlandIPC | None, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    def send(line: str) -> None:
        stdout.write(line + "\n")
        stdout.flush()

    session = RpcSession(service, send, ipc)
    try:
        for line in stdin:
            session.handle_line(line)
    except KeyboardInterrupt:
        pass
    finally:
        session.close()
    return 0
