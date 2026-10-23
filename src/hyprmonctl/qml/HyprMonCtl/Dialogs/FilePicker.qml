import QtQuick
import QtQuick.Dialogs

// Kept in its own file and loaded on demand: if QtQuick.Dialogs is unavailable in a
// host, only the "Browse…" button disappears.
FileDialog {
    nameFilters: ["Lua files (*.lua)", "All files (*)"]
    fileMode: FileDialog.SaveFile
    options: FileDialog.DontConfirmOverwrite
}
