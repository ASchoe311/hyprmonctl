"""In-process line transport between QML and the JSON-RPC session."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal, Slot

from hyprmonctl.hyprland.ipc import HyprlandIPC
from hyprmonctl.rpc.session import RpcSession
from hyprmonctl.service import MonitorService


class InProcessTransport(QObject):
    """QML-facing transport: `send(line)` in, `messageReceived(line)` out.

    Requests run on one worker thread (so the UI never blocks on Hyprland IPC, and
    requests stay ordered). Signals emitted from that thread are queued to the GUI thread.
    """

    messageReceived = Signal(str, arguments=["line"])

    def __init__(self, service: MonitorService, ipc: HyprlandIPC | None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hyprmonctl-rpc")
        self._session = RpcSession(service, self.messageReceived.emit, ipc)

    @Slot(str)
    def send(self, line: str) -> None:
        self._executor.submit(self._session.handle_line, line)

    def close(self) -> None:
        self._executor.shutdown(wait=True)
        self._session.close()
