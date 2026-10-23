"""JSON-RPC 2.0 method table over `MonitorService`.

Every client (the bundled GUI, Quickshell, scripts) uses these methods:

    api.version                      -> {"version", "apiVersion"}
    state.get                        -> AppState
    layout.validate  {draft}         -> ValidationResult
    config.render    {draft}         -> {"lua"}
    config.preview   {draft}         -> PreviewInfo    (auto-reverts unless confirmed)
    config.confirm                   -> SaveResult
    config.revert                    -> {"reverted"}
    config.save      {draft}         -> SaveResult     (write without previewing)
    settings.get                     -> Settings
    settings.update  {patch}         -> Settings
    theme.get                        -> {"colors"}

Notifications pushed to clients: monitors.changed, preview.started, preview.reverted,
config.saved, settings.changed.
"""

from __future__ import annotations

import json
import traceback
from typing import Any, Callable

from hyprmonctl import API_VERSION, __version__
from hyprmonctl.hyprland.ipc import HyprlandError, HyprlandUnavailable
from hyprmonctl.model.state import Draft
from hyprmonctl.serialize import to_json
from hyprmonctl.service import ConflictError, InvalidDraftError, MonitorService, NoPreviewError

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
HYPRLAND_UNAVAILABLE = -32000
HYPRLAND_ERROR = -32001
FILE_CONFLICT = -32002
INVALID_DRAFT = -32003
NO_PREVIEW = -32004


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _draft(params: dict[str, Any]) -> Draft:
    return Draft.from_json(params.get("draft"))


class Dispatcher:
    def __init__(self, service: MonitorService) -> None:
        s = service
        self._methods: dict[str, Callable[[dict[str, Any]], Any]] = {
            "api.version": lambda p: {"version": __version__, "apiVersion": API_VERSION},
            "state.get": lambda p: s.state(),
            "layout.validate": lambda p: s.validate(_draft(p)),
            "config.render": lambda p: {"lua": s.render(_draft(p))},
            "config.preview": lambda p: s.preview(_draft(p)),
            "config.confirm": lambda p: s.confirm(),
            "config.revert": lambda p: {"reverted": s.revert()},
            "config.save": lambda p: s.save(_draft(p)),
            "settings.get": lambda p: s.settings,
            "settings.update": lambda p: s.update_settings(p.get("patch") or {}),
            "theme.get": lambda p: {"colors": s.theme()},
        }

    @property
    def methods(self) -> list[str]:
        return sorted(self._methods)

    def handle_line(self, line: str) -> str | None:
        """Handle one request line; returns the response line, or None for notifications."""
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            return _encode(_error_response(None, RpcError(PARSE_ERROR, f"parse error: {exc}")))
        response = self.handle(request)
        return None if response is None else _encode(response)

    def handle(self, request: Any) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return _error_response(None, RpcError(INVALID_REQUEST, "invalid JSON-RPC 2.0 request"))
        request_id = request.get("id")
        is_notification = "id" not in request
        try:
            method = self._methods.get(request["method"])
            if method is None:
                raise RpcError(METHOD_NOT_FOUND, f"unknown method {request['method']!r}")
            params = request.get("params") or {}
            if not isinstance(params, dict):
                raise RpcError(INVALID_PARAMS, "params must be an object")
            result = to_json(_call(method, params))
        except RpcError as exc:
            return None if is_notification else _error_response(request_id, exc)
        return None if is_notification else {"jsonrpc": "2.0", "id": request_id, "result": result}


def _call(method: Callable[[dict[str, Any]], Any], params: dict[str, Any]) -> Any:
    try:
        return method(params)
    except RpcError:
        raise
    except HyprlandUnavailable as exc:
        raise RpcError(HYPRLAND_UNAVAILABLE, str(exc)) from exc
    except HyprlandError as exc:
        raise RpcError(HYPRLAND_ERROR, f"Hyprland: {exc}") from exc
    except ConflictError as exc:
        raise RpcError(FILE_CONFLICT, str(exc)) from exc
    except InvalidDraftError as exc:
        raise RpcError(INVALID_DRAFT, str(exc), to_json(exc.issues)) from exc
    except NoPreviewError as exc:
        raise RpcError(NO_PREVIEW, str(exc)) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise RpcError(INVALID_PARAMS, str(exc)) from exc
    except OSError as exc:
        raise RpcError(INTERNAL_ERROR, f"{exc.strerror or exc}: {exc.filename or ''}".rstrip(": ")) from exc
    except Exception as exc:  # noqa: BLE001 - report anything else to the client instead of dying
        raise RpcError(INTERNAL_ERROR, f"internal error: {exc}", traceback.format_exc()) from exc


def notification(method: str, params: dict[str, Any]) -> str:
    return _encode({"jsonrpc": "2.0", "method": method, "params": to_json(params)})


def _error_response(request_id: Any, error: RpcError) -> dict[str, Any]:
    body: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.data is not None:
        body["data"] = error.data
    return {"jsonrpc": "2.0", "id": request_id, "error": body}


def _encode(message: dict[str, Any]) -> str:
    return json.dumps(message, separators=(",", ":"))
