import io
import json

from hyprmonctl.rpc import dispatcher as rpc
from hyprmonctl.rpc.dispatcher import Dispatcher
from hyprmonctl.rpc.stdio import serve_stdio


def call(dispatcher, method, params=None, id=1):
    request = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        request["params"] = params
    return json.loads(dispatcher.handle_line(json.dumps(request)))


def test_state_and_validate_roundtrip(env):
    d = Dispatcher(env.service)
    state = call(d, "state.get")["result"]
    assert state["monitors"][1]["config"]["output"] == "desc:Dell Inc. DELL P2725QE FKYZQB4"
    assert state["monitors"][1]["live"]["logicalWidth"] == 1920
    draft = {
        "monitors": [m["config"] for m in state["monitors"]],
        "keepRules": [r["index"] for r in state["savedRules"]],
        "fileHash": state["fileHash"],
    }
    result = call(d, "layout.validate", {"draft": draft})["result"]
    assert result["issues"] == []
    lua = call(d, "config.render", {"draft": draft})["result"]["lua"]
    assert "S3422DWG" in lua


def test_errors(env):
    d = Dispatcher(env.service)
    assert call(d, "nope")["error"]["code"] == rpc.METHOD_NOT_FOUND
    assert call(d, "layout.validate", {"draft": {"monitors": "x"}})["error"]["code"] == rpc.INVALID_PARAMS
    assert call(d, "config.confirm")["error"]["code"] == rpc.NO_PREVIEW
    assert json.loads(d.handle_line("{"))["error"]["code"] == rpc.PARSE_ERROR
    assert json.loads(d.handle_line('{"id": 1}'))["error"]["code"] == rpc.INVALID_REQUEST
    assert d.handle_line('{"jsonrpc": "2.0", "method": "api.version"}') is None  # notification


def test_invalid_draft_carries_issues(env):
    d = Dispatcher(env.service)
    state = call(d, "state.get")["result"]
    configs = [m["config"] for m in state["monitors"]]
    configs[1]["position"] = "100x0"
    reply = call(d, "config.preview", {"draft": {"monitors": configs}})
    assert reply["error"]["code"] == rpc.INVALID_DRAFT
    assert reply["error"]["data"][0]["code"] == "overlap"


def test_stdio_server_streams_responses_and_notifications(env):
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"settings.update","params":{"patch":{"snapDistance":8}}}\n'
        '\n'
        '{"jsonrpc":"2.0","id":2,"method":"api.version"}\n'
    )
    stdout = io.StringIO()
    assert serve_stdio(env.service, None, stdin, stdout) == 0
    lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert lines[0] == {"jsonrpc": "2.0", "method": "settings.changed", "params": {}}
    assert lines[1]["result"]["snapDistance"] == 8
    assert lines[2]["result"]["apiVersion"] == 1
