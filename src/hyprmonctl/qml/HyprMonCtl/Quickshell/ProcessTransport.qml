import QtQuick
import Quickshell.Io

// Transport for Quickshell: runs `hyprmonctl serve` as a child process and speaks
// newline-delimited JSON-RPC over its stdin/stdout. Stopping the process (running =
// false, or destroying this object) makes the backend revert any unconfirmed preview.
QtObject {
    id: transport

    property list<string> command: ["hyprmonctl", "serve"]
    property bool running: true
    readonly property bool connected: process.running

    signal messageReceived(string line)
    signal disconnected(int exitCode)

    function send(line) {
        if (!process.running) {
            console.warn("hyprmonctl: backend is not running; dropping request");
            return;
        }
        process.write(line + "\n");
    }

    readonly property Process process: Process {
        command: transport.command
        running: transport.running
        stdinEnabled: true
        stdout: SplitParser {
            onRead: data => transport.messageReceived(data)
        }
        stderr: SplitParser {
            onRead: data => console.warn("hyprmonctl:", data)
        }
        onExited: (exitCode, exitStatus) => transport.disconnected(exitCode)
    }
}
