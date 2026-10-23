"""Request/response client for Hyprland's command socket (what `hyprctl` uses)."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, Protocol

from hyprmonctl.model.monitor import MonitorInfo


class HyprlandError(RuntimeError):
    """Hyprland rejected a request."""


class HyprlandUnavailable(HyprlandError):
    """No running Hyprland instance could be reached."""


class Compositor(Protocol):
    """The operations the service needs from Hyprland; tests substitute a fake."""

    def monitors(self) -> list[MonitorInfo]: ...

    def eval(self, code: str) -> None: ...

    def reload(self) -> None: ...

    def config_errors(self) -> list[str]: ...


def instance_dir(signature: str | None = None) -> Path:
    signature = signature or os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not signature:
        raise HyprlandUnavailable("HYPRLAND_INSTANCE_SIGNATURE is not set; is Hyprland running?")
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(runtime) / "hypr" / signature


class HyprlandIPC:
    def __init__(self, signature: str | None = None, timeout: float = 5.0) -> None:
        self._signature = signature
        self._timeout = timeout

    @property
    def socket_path(self) -> Path:
        return instance_dir(self._signature) / ".socket.sock"

    @property
    def event_socket_path(self) -> Path:
        return instance_dir(self._signature) / ".socket2.sock"

    def request(self, command: str) -> str:
        path = self.socket_path
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(self._timeout)
                sock.connect(str(path))
                sock.sendall(command.encode())
                chunks = []
                while chunk := sock.recv(65536):
                    chunks.append(chunk)
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise HyprlandUnavailable(f"cannot connect to Hyprland at {path}") from exc
        except OSError as exc:
            raise HyprlandError(f"Hyprland IPC failed: {exc}") from exc
        return b"".join(chunks).decode("utf-8", errors="replace")

    def request_json(self, command: str) -> Any:
        reply = self.request("j/" + command)
        try:
            return json.loads(reply)
        except json.JSONDecodeError as exc:
            raise HyprlandError(f"unexpected reply to {command!r}: {reply[:200]}") from exc

    def monitors(self) -> list[MonitorInfo]:
        return [MonitorInfo.from_hyprctl(item) for item in self.request_json("monitors all")]

    def eval(self, code: str) -> None:
        reply = self.request("eval " + code).strip()
        if reply != "ok":
            raise HyprlandError(reply.removeprefix("error:").strip() or "eval failed")

    def reload(self) -> None:
        reply = self.request("reload").strip()
        if reply != "ok":
            raise HyprlandError(f"reload failed: {reply}")

    def config_errors(self) -> list[str]:
        return [line for line in self.request_json("configerrors") if line.strip()]
