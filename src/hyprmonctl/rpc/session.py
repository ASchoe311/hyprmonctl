"""One client connection: request handling plus pushed notifications, over any line transport."""

from __future__ import annotations

import threading
from typing import Callable

from hyprmonctl.hyprland.events import MonitorEventListener
from hyprmonctl.hyprland.ipc import HyprlandError, HyprlandIPC
from hyprmonctl.rpc.dispatcher import Dispatcher, notification
from hyprmonctl.service import MonitorService


class RpcSession:
    """Binds a `MonitorService` to a `send(line)` callable.

    Responses and notifications may originate on different threads, so sends are
    serialized. Closing the session reverts any preview the client left pending.
    """

    def __init__(
        self,
        service: MonitorService,
        send: Callable[[str], None],
        ipc: HyprlandIPC | None = None,
    ) -> None:
        self._service = service
        self._send = send
        self._send_lock = threading.Lock()
        self._dispatcher = Dispatcher(service)
        self._unsubscribe = service.subscribe(self._on_event)
        self._listener: MonitorEventListener | None = None
        if ipc is not None:
            try:
                self._listener = MonitorEventListener(ipc.event_socket_path, service.notify_monitors_changed)
                self._listener.start()
            except HyprlandError:
                self._listener = None

    def _write(self, line: str) -> None:
        with self._send_lock:
            self._send(line)

    def _on_event(self, event: str, payload: dict) -> None:
        self._write(notification(event, payload))

    def handle_line(self, line: str) -> None:
        if not line.strip():
            return
        response = self._dispatcher.handle_line(line)
        if response is not None:
            self._write(response)

    def close(self) -> None:
        if self._listener:
            self._listener.stop()
        self._unsubscribe()
        self._service.close()
