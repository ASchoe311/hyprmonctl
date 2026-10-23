"""Drive `hyprmonctl serve` from a script, isolated from the user's settings.

    import sys; sys.path.insert(0, "tools")
    from backend import Backend

    with Backend(lua_path="/tmp/scratch/monitors.lua") as b:
        state = b.call("state.get")
        draft = Backend.draft(state)
        draft["monitors"][1]["position"] = "1600x80"
        b.call("config.preview", draft=draft)       # live change, auto-reverts after the timeout
        print(b.live())                              # {name: (x, y, scale)} from hyprctl
        b.call("config.revert")
        b.wait_for("preview.reverted")

Settings go to a throwaway XDG_CONFIG_HOME, so settings.update can't touch
~/.config/hyprmonctl. Always pass a scratch lua_path when anything might save.
Closing the backend (or leaving the `with` block) reverts any pending preview.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]


class RpcError(RuntimeError):
    def __init__(self, error: dict[str, Any]) -> None:
        super().__init__(f"{error.get('code')}: {error.get('message')}")
        self.error = error


class Backend:
    def __init__(self, lua_path: str | os.PathLike[str], config_home: str | None = None, exe: str | None = None) -> None:
        self._tmp = None if config_home else tempfile.TemporaryDirectory(prefix="hyprmonctl-test-")
        env = dict(os.environ, XDG_CONFIG_HOME=config_home or self._tmp.name)
        command = [exe or str(REPO / ".venv" / "bin" / "hyprmonctl"), "--lua-path", str(lua_path), "serve"]
        self._proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env, bufsize=1)
        self._next_id = 0
        self.notifications: list[dict[str, Any]] = []

    def __enter__(self) -> Backend:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _read(self, timeout: float) -> dict[str, Any] | None:
        ready, _, _ = select.select([self._proc.stdout], [], [], timeout)
        if not ready:
            return None
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("hyprmonctl serve exited")
        return json.loads(line)

    def call(self, method: str, **params: Any) -> Any:
        """Send a request and return its result; notifications seen meanwhile are recorded."""
        self._next_id += 1
        request = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()
        while True:
            message = self._read(30)
            if message is None:
                raise TimeoutError(f"no reply to {method}")
            if message.get("id") == self._next_id:
                if "error" in message:
                    raise RpcError(message["error"])
                return message["result"]
            self.notifications.append(message)

    def wait_for(self, method: str, timeout: float = 30) -> dict[str, Any]:
        """Block until a notification named `method` arrives; returns its params."""
        deadline = time.time() + timeout
        for seen in self.notifications:
            if seen.get("method") == method:
                self.notifications.remove(seen)
                return seen.get("params", {})
        while time.time() < deadline:
            message = self._read(max(0.0, deadline - time.time()))
            if message and message.get("method") == method:
                return message.get("params", {})
            if message:
                self.notifications.append(message)
        raise TimeoutError(f"no {method} notification within {timeout}s")

    @staticmethod
    def draft(state: dict[str, Any]) -> dict[str, Any]:
        """The draft that reproduces the file as-is (edit it before previewing)."""
        return {
            "monitors": [dict(m["config"]) for m in state["monitors"]],
            "keepRules": [r["index"] for r in state["savedRules"]],
            "fileHash": state["fileHash"],
        }

    @staticmethod
    def live() -> dict[str, tuple[int, int, float]]:
        """Current monitor geometry straight from Hyprland, for before/after comparisons."""
        monitors = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"]))
        return {m["name"]: (m["x"], m["y"], m["scale"]) for m in monitors}

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.stdin.close()
            self._proc.wait(timeout=10)
        if self._tmp:
            self._tmp.cleanup()
