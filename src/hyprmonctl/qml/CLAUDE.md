# qml/: the UI (shared by the standalone app and Quickshell)

`Main.qml` is the standalone window: an `ApplicationWindow` with a required
`transport`, injected by `gui/app.py`. Everything else is the `HyprMonCtl` module
family. This directory is the import path (`hyprmonctl qml-path` prints it).

## Module layout: one URI module per directory

| Module (dir) | Contents | May import |
|---|---|---|
| `HyprMonCtl` | `MonitorConfigurator` (the embeddable page), `MonitorStore` (client state), `RpcClient` | all below |
| `HyprMonCtl.Style` | `Theme` singleton (tokens, `applyPalette(matugenColors)`, `severityColor`) | – |
| `HyprMonCtl.Controls` | primitives: `Card`, `SettingsRow`, `HComboBox`, `HSwitch`, `HButton`, `HIconButton`, `HTextField`, `HStepper`, `HTabBar`, `ModalDialog`, `Toast`, `Icon` (+ `Icons.js` SVG paths), `HLabel` | Style |
| `HyprMonCtl.Layout` | `LayoutCanvas`, `MonitorTile`, `Geometry.js`, `Snapping.js` (see `Layout/CLAUDE.md`) | Style, Controls |
| `HyprMonCtl.Panels` | settings rows and cards; `Format.js` holds labels and option lists (transforms, VRR, color presets) | Style, Controls, Layout |
| `HyprMonCtl.Dialogs` | `ConfirmChangesDialog`, `LuaPreviewDialog`, `SettingsDialog`, `FilePicker` (loaded lazily) | Style, Controls |
| `HyprMonCtl.Quickshell` | adapter; the **only** place `import Quickshell*` is allowed | HyprMonCtl, Style |

- **Imports go by URI** (`import HyprMonCtl.Controls`), never by relative directory,
  or the `Theme` singleton can be instantiated twice. JS files inside a module import
  relatively (`import "Geometry.js" as Geometry`).
- **No cycles:** `Panels`, `Dialogs` and `Layout` never import the root `HyprMonCtl`.
  They receive `store` as a property.
- **New files** must be added to that directory's `qmldir`.

## Data flow

- **Transport contract:** any object with `send(string)` and a
  `messageReceived(string line)` signal.
- **`RpcClient`:** `call(method, params, onResult, onError)`, plus
  `notification(method, params)`.
- **`MonitorStore`** (one per configurator, not a singleton):
  - **Data:** `state` (last `state.get`); `configs` (the draft, parallel to
    `state.monitors`, **replaced, never mutated in place**); `keepRules`; `revision`
    (bumped on every edit); `dirty` (compared against a JSON baseline); `issues` (from
    a debounced `layout.validate`, ignored if stale); `previewDeadline`.
  - **Edits:** `select`, `setField(s)`, `moveMonitor` (pins every auto-placed monitor
    where it's shown), `arrangeRow`, `removeSavedRule`, `restoreSavedRules`, `discard`.
  - **Actions:** `apply` (preview), `keep`, `revert`, `saveWithoutPreview`,
    `renderLua`, `updateSettings`.
  - **Notifications:** `monitors.changed` triggers `refresh(true)`, which keeps the
    draft if the file hash is unchanged.
- **Panels** take `store` and `name`, and derive `entry`/`config` with
  `store.entry(name)`/`store.config(name)`. Dependencies are tracked through those
  calls, so no dummy `store.revision;` statements are needed.
- **Embed API** of `MonitorConfigurator`:
  - Properties: `transport`, `showHeader`, `followShellTheme`, `store` (read-only).
  - Functions: `showLua()`, `showSettings()`.
  - `objectName: "configurator"` in `Main.qml` is what `tools/render_ui.py` finds.

## Conventions

- **Colors and sizes** come from `Theme` only. Text uses `HLabel`. Rows are
  `SettingsRow` inside a `Card`, with the label on the left and controls on the right
  (COSMIC layout).
- **Delegates:** files with delegates use `pragma ComponentBehavior: Bound` with
  `required property var modelData`, accessed through the delegate's id.
- **Guard bindings against null** `entry`/`config`; panels exist before the first
  `state.get` arrives.
- **Qt versions:** it must run on PySide6's Qt (6.12) **and** the system Qt that
  Quickshell uses (6.11). Rectangle's per-corner radii (Qt 6.7) are the newest API in
  use.

## Gotchas (each one cost a debugging session)

- **No `on` + capital names:** a property named like `onAccent` parses as a signal
  handler. Use `accentText` and similar.
- **Animated properties:** don't read back a property that has a `Behavior` right
  after assigning it; you get the in-flight animated value. Compute from a local (see
  `LayoutCanvas.refit`).
- **Drags inside the page ScrollView:** a `MouseArea` needs `preventStealing: true`,
  or the Flickable steals vertical drags and cancels them.
- **Layout minimum widths:** one wide child (e.g. a long path) can force a
  `ColumnLayout` wider than the window. Cap it with `Layout.maximumWidth` plus elide.
- **Binding loops:** don't bind a child's width to its `Row`'s width. Compute natural
  sizes from `Text.implicitWidth` (see `HTabBar`).
- **`HComboBox`** syncs `currentIndex` imperatively (`sync()`), because the control
  overwrites a bound `currentIndex` on activation. Drive it with `value` and `options`
  (`[{text, value, detail?}]`) and react to `picked(value)`.
- **`HSwitch`** is not checkable. `checked` is bound to the model, and the owner
  handles `onClicked`.
- **Startup order:** `MonitorStore` refreshes on transport change via `Qt.callLater`,
  because the child `RpcClient`'s binding updates after the parent's change handler.
- **Dialogs** are in-scene `ModalDialog` items, not `Popup`s, so they work in any host
  window. The body scrolls; the title and buttons stay pinned. ComboBox popups are fine.

## Verify

Use offscreen screenshots via `tools/render_ui.py` (`hyprmonctl-verify` skill), and
qmllint. Test a short, narrow window too: tiled windows are often ~780x470.
