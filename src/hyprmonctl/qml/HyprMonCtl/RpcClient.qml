import QtQuick

// JSON-RPC 2.0 client over a line transport. The transport is any object with
// `send(string line)` and a `messageReceived(string line)` signal: the PySide6 host
// provides one in-process, HyprMonCtl.Quickshell provides one over a child process.
QtObject {
    id: client

    property var transport: null
    property int _nextId: 1
    property var _pending: ({})

    signal notification(string method, var params)

    readonly property Connections _connections: Connections {
        target: client.transport
        ignoreUnknownSignals: true
        function onMessageReceived(line) {
            client._receive(line);
        }
    }

    function call(method, params, onResult, onError) {
        if (!transport) {
            if (onError)
                onError({ code: -1, message: "Not connected to the hyprmonctl backend" });
            return;
        }
        const id = _nextId++;
        _pending[id] = { onResult: onResult, onError: onError };
        transport.send(JSON.stringify({ jsonrpc: "2.0", id: id, method: method, params: params || {} }));
    }

    // Fail every in-flight call, e.g. when the backend process died.
    function failPending(message) {
        const pending = _pending;
        _pending = {};
        for (const id in pending)
            if (pending[id].onError)
                pending[id].onError({ code: -1, message: message });
    }

    function _receive(line) {
        let msg;
        try {
            msg = JSON.parse(line);
        } catch (e) {
            console.warn("hyprmonctl: ignoring non-JSON backend output:", line);
            return;
        }
        if (msg.id === undefined || msg.id === null) {
            if (msg.method)
                notification(msg.method, msg.params || {});
            else if (msg.error)
                console.warn("hyprmonctl:", msg.error.message);
            return;
        }
        const handlers = _pending[msg.id];
        delete _pending[msg.id];
        if (!handlers)
            return;
        if (msg.error) {
            if (handlers.onError)
                handlers.onError(msg.error);
            else
                console.warn("hyprmonctl:", msg.error.message);
        } else if (handlers.onResult) {
            handlers.onResult(msg.result);
        }
    }
}
