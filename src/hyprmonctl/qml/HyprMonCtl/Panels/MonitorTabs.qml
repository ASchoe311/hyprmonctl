import QtQuick
import QtQuick.Layouts
import HyprMonCtl.Controls

HTabBar {
    id: tabs

    required property var store

    Layout.fillWidth: true
    currentKey: store.selectedName
    tabs: store.monitors.map(m => {
        const config = store.config(m.name);
        const off = !!config && !config.enabled;
        return { key: m.name, badge: m.id + 1, text: m.label + (off ? " (off)" : ""), dim: off };
    })
    onSelected: key => store.select(key)
}
