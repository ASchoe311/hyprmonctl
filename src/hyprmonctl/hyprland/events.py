"""Listener for Hyprland's event socket (`.socket2.sock`)."""

from __future__ import annotations

import socket
import threading
from pathlib import Path
from typing import Callable

MONITOR_EVENTS = frozenset(
    {"monitoradded", "monitoraddedv2", "monitorremoved", "monitorremovedv2", "configreloaded"}
)


class MonitorEventListener:
    """Calls `on_change(event)` (debounced) whenever monitors are hotplugged or the config reloads."""

    def __init__(
        self,
        socket_path: Path,
        on_change: Callable[[str], None],
        debounce: float = 0.3,
        reconnect_delay: float = 2.0,
    ) -> None:
        self._path = socket_path
        self._on_change = on_change
        self._debounce = debounce
        self._reconnect_delay = reconnect_delay
        self._stop = threading.Event()
        self._sock: socket.socket | None = None
        self._timer: threading.Timer | None = None
        self._last_event = ""
        self._thread = threading.Thread(target=self._run, name="hypr-events", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._timer:
            self._timer.cancel()
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    self._sock = sock
                    sock.connect(str(self._path))
                    self._read(sock)
            except OSError:
                pass
            self._stop.wait(self._reconnect_delay)

    def _read(self, sock: socket.socket) -> None:
        buffer = b""
        while not self._stop.is_set():
            chunk = sock.recv(4096)
            if not chunk:
                return
            buffer += chunk
            *lines, buffer = buffer.split(b"\n")
            for line in lines:
                event = line.split(b">>", 1)[0].decode(errors="replace")
                if event in MONITOR_EVENTS:
                    self._schedule(event)

    def _schedule(self, event: str) -> None:
        self._last_event = event
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self._debounce, lambda: self._on_change(self._last_event))
        self._timer.daemon = True
        self._timer.start()
