import QtQuick
import HyprMonCtl.Layout

// Client-side state: the backend snapshot plus the user's unsaved draft.
// Every edit replaces `configs` and bumps `revision`, which views bind to.
QtObject {
    id: store

    property var transport: null
    readonly property RpcClient rpc: RpcClient {
        transport: store.transport
        onNotification: (method, params) => store._onNotification(method, params)
    }

    property var state: null
    property string loadError: ""
    property bool loading: false
    property bool busy: false

    property var configs: []        // MonitorConfig per entry in `monitors` (same order)
    property var keepRules: []      // indices of saved rules to keep in the file
    property int revision: 0
    property bool dirty: false
    property string selectedName: ""
    property var issues: []         // from layout.validate, for the current revision
    property real previewDeadline: 0
    property int previewTimeout: 0
    property string _baseline: ""

    readonly property var monitors: state ? state.monitors : []
    readonly property var savedRules: state ? state.savedRules : []
    readonly property var diagnostics: state ? state.diagnostics : []
    readonly property var settings: state ? state.settings : ({})
    readonly property bool previewActive: previewDeadline > 0
    readonly property var errors: issues.filter(i => i.severity === "error")
    readonly property bool canApply: dirty && errors.length === 0 && !busy && !previewActive

    signal message(string text, string kind)

    readonly property Timer _validateTimer: Timer {
        interval: 120
        onTriggered: store.validate()
    }

    // Deferred so the RpcClient's own `transport` binding has updated first.
    onTransportChanged: Qt.callLater(refresh, false)
    Component.onCompleted: Qt.callLater(refresh, false)

    // --- queries ---------------------------------------------------------------------

    function indexOf(name) {
        for (let i = 0; i < monitors.length; ++i)
            if (monitors[i].name === name)
                return i;
        return -1;
    }
    function entry(name) {
        const i = indexOf(name);
        return i >= 0 ? monitors[i] : null;
    }
    function config(name) {
        const i = indexOf(name);
        return i >= 0 ? configs[i] : null;
    }
    function issuesFor(name, codes) {
        return issues.filter(i => i.monitors.indexOf(name) >= 0 && (!codes || codes.indexOf(i.code) >= 0));
    }
    function enabledCount() {
        return configs.filter(c => c.enabled).length;
    }
    function draft() {
        return { monitors: configs, keepRules: keepRules, fileHash: state ? state.fileHash : null };
    }

    // --- loading ---------------------------------------------------------------------

    function refresh(keepDraft) {
        if (!transport)
            return;
        loading = true;
        rpc.call("state.get", {}, s => {
            loading = false;
            loadError = "";
            _applyState(s, keepDraft);
        }, e => {
            loading = false;
            loadError = e.message;
        });
    }

    function _applyState(s, keepDraft) {
        const sameFile = state && s.fileHash === state.fileHash;
        const previous = keepDraft && dirty && sameFile ? configs : null;
        const freshConfigs = s.monitors.map(m => Object.assign({}, m.config));
        const freshKeep = s.savedRules.map(r => r.index);
        if (keepDraft && dirty && !sameFile)
            message(s.luaPathDisplay + " changed on disk; your unsaved changes were reset.", "info");

        state = s;
        previewDeadline = s.preview ? s.preview.deadline : 0;
        previewTimeout = s.preview ? s.preview.timeout : 0;
        _baseline = _snapshot(freshConfigs, freshKeep);
        if (previous) {
            // Keep edits for monitors that are still connected; new ones start from the file.
            configs = freshConfigs.map(c => previous.find(p => p.name === c.name) || c);
            keepRules = keepRules.filter(i => freshKeep.indexOf(i) >= 0);
        } else {
            configs = freshConfigs;
            keepRules = freshKeep;
        }
        if (indexOf(selectedName) < 0) {
            const focused = s.monitors.find(m => m.focused);
            selectedName = focused ? focused.name : (s.monitors.length ? s.monitors[0].name : "");
        }
        _commit();
    }

    function _snapshot(cfgs, keep) {
        return JSON.stringify([cfgs, keep.slice().sort((a, b) => a - b)]);
    }

    function _commit() {
        revision++;
        dirty = _snapshot(configs, keepRules) !== _baseline;
        _validateTimer.restart();
    }

    function validate() {
        if (!state)
            return;
        const rev = revision;
        rpc.call("layout.validate", { draft: draft() }, r => {
            if (rev === revision)
                issues = r.issues;
        }, e => console.warn("hyprmonctl: validate failed:", e.message));
    }

    // --- edits -----------------------------------------------------------------------

    function select(name) {
        selectedName = name;
    }

    function setField(name, key, value) {
        const patch = {};
        patch[key] = value;
        setFields(name, patch);
    }

    function setFields(name, patch) {
        const i = indexOf(name);
        if (i < 0)
            return;
        const next = configs.slice();
        next[i] = Object.assign({}, next[i], patch);
        configs = next;
        _commit();
    }

    // Arranging by hand pins every auto-placed monitor where it is currently shown, so
    // Hyprland's auto placement can't rearrange them differently after applying.
    function moveMonitor(name, x, y) {
        const rects = Geometry.layoutRects(monitors, configs);
        configs = configs.map(c => {
            if (c.name === name)
                return Object.assign({}, c, { position: Geometry.formatPosition(x, y) });
            const r = rects.find(r => r.name === c.name);
            return r && r.auto ? Object.assign({}, c, { position: Geometry.formatPosition(r.x, r.y) }) : c;
        });
        _commit();
    }

    function arrangeRow() {
        const placed = Geometry.arrangeRow(Geometry.layoutRects(monitors, configs));
        configs = configs.map(c => placed[c.name] ? Object.assign({}, c, { position: Geometry.formatPosition(placed[c.name].x, placed[c.name].y) }) : c);
        _commit();
    }

    function removeSavedRule(index) {
        keepRules = keepRules.filter(i => i !== index);
        _commit();
    }

    function restoreSavedRules() {
        keepRules = savedRules.map(r => r.index);
        _commit();
    }

    function discard() {
        if (state)
            _applyState(state, false);
    }

    // --- actions ---------------------------------------------------------------------

    function _fail(e) {
        busy = false;
        message(e.message, "error");
    }

    function apply() {
        busy = true;
        rpc.call("config.preview", { draft: draft() }, info => {
            busy = false;
            previewDeadline = info.deadline;
            previewTimeout = info.timeout;
        }, _fail);
    }

    function keep() {
        busy = true;
        rpc.call("config.confirm", {}, result => {
            busy = false;
            previewDeadline = 0;
            _reportSaved(result);
        }, e => {
            previewDeadline = 0;
            _fail(e);
            refresh(true);
        });
    }

    function saveWithoutPreview() {
        busy = true;
        rpc.call("config.save", { draft: draft() }, result => {
            busy = false;
            _reportSaved(result);
        }, _fail);
    }

    function _reportSaved(result) {
        if (result.configErrors.length)
            message("Saved, but Hyprland reports: " + result.configErrors.join("; "), "error");
        else
            message("Saved to " + (state ? state.luaPathDisplay : result.path), "success");
        refresh(false);
    }

    function revert() {
        rpc.call("config.revert", {}, () => previewDeadline = 0, _fail);
    }

    function renderLua(callback) {
        rpc.call("config.render", { draft: draft() }, r => callback(r.lua, ""), e => callback("", e.message));
    }

    function updateSettings(patch, callback) {
        rpc.call("settings.update", { patch: patch }, () => {
            if (callback)
                callback("");
            refresh(false);
        }, e => {
            if (callback)
                callback(e.message);
        });
    }

    function _onNotification(method, params) {
        if (method === "monitors.changed") {
            if (!previewActive && !busy)
                refresh(true);
        } else if (method === "preview.started") {
            previewDeadline = params.deadline;
            previewTimeout = params.timeout;
        } else if (method === "preview.reverted") {
            previewDeadline = 0;
            if (params.error)
                message("Couldn't fully restore the previous settings: " + params.error, "error");
            else if (params.reason === "timeout")
                message("No confirmation, so the previous display settings were restored.", "info");
        }
    }
}
