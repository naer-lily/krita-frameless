Vibe-coded with deepseek-v4-pro.

# Frameless — Krita Plugin

> [中文版](README_cn.md)

**Not just frameless — the titlebar is fully customizable, and you can embed Krita's own toolbars directly into it.** Remove the native Windows titlebar, then build your own compact header with any combination of components: document name, menus, spacers, window controls, and even Krita's native QToolBars — all in one row. Drag empty space to move the window, double-click to toggle maximise.

Layout is driven by a simple `config.json` file. On first run (or if the file is missing / corrupt), a template `config.json` is written to disk automatically — just edit it and restart Krita. Components are modular — drop a new `.py` file into `components/` and register it to add your own.

**Windows 10 / 11 only.** Other operating systems are unaffected (the plugin silently skips non-Windows messages at load time).

![](image.png)

## Installation

refer <https://github.com/naer-lily/krita-shortcut-fix>. **A manual restart is required**.

## Visual comparison

```
Native Krita:
┌─────────────────────────────────────────────┐
│  untitled.kra  —  Krita         ─  □  ✕  │  ← native titlebar
├─────────────────────────────────────────────┤
│  File  Edit  View  ...                      │  ← menu bar
├─────────────────────────────────────────────┤
│  canvas                                      │
└─────────────────────────────────────────────┘

Frameless:
┌──────────────────────────────────────────────────┐
│  doc.kra  ☰  [brush size ████]  [tool buttons]  ─  □  ✕  │  ← custom titlebar
├──────────────────────────────────────────────────┤
│  canvas                                           │
└──────────────────────────────────────────────────┘
```

- Current document name shown on the left, falling back to `Untitled` when no document is open
- Menus can be shown inline OR collapsed into a single icon button with dropdown — Alt+letter shortcuts preserved in both modes
- **Photoshop-style tool slots** — one button per tool group; click activates, double-click / right-click swaps which tool the slot holds
- **Krita's native toolbars can be embedded directly into the titlebar** via the `CustomToolBar` component — reclaim vertical screen space
- Empty titlebar space can be dragged to move the window; Aero Snap (half-screen / quarter-screen) works when dragged to a screen edge
- Double-click empty titlebar space to toggle maximise / restore
- Titlebar height dynamically adapts to the tallest component (e.g. toolbar taller than menu)
- Layout is configurable via `config.json` — reorder, remove, or add custom components

### Configuration

Edit `frameless/config.json` to customize the titlebar layout.
If the file is deleted or corrupted, a fresh template is written on next launch.

This is the template that gets written on first run (shown compactly):

```json
{
    "layout": [
        {"name": "Separator",       "config": {"width": 4}},
        {"name": "OriginalMenuBar", "config": {"compact": true}},
        {"name": "CurrentFileName", "config": {"poll_ms": 500}},
        {"name": "ToolSlot", "config": {"id": "brush",  "tools": ["KritaShape/KisToolBrush"]}},
        {"name": "ToolSlot", "config": {"id": "select", "tools": ["KisToolSelectOutline", "KisToolSelectElliptical", "KisToolSelectRectangular", "KisToolSelectPolygonal", "KisToolSelectSimilar", "KisToolSelectMagnetic"]}},
        {"name": "ToolSlot", "config": {"id": "shape",  "tools": ["KisToolPolyline", "KritaShape/KisToolLine", "KritaShape/KisToolRectangle", "KritaShape/KisToolEllipse"]}},
        {"name": "ToolSlot", "config": {"id": "fill",   "tools": ["KritaFill/KisToolFill", "KritaFill/KisToolGradient", "KritaShape/KisToolLazyBrush"]}},
        {"name": "ToolSlot", "config": {"id": "misc",   "tools": ["ToolReferenceImages", "KisToolCrop", "KritaShape/KisToolMeasure", "KisAssistantTool", "SvgTextTool", "KritaSelected/KisToolColorSampler"]}},
        {"name": "Spacer",          "config": {"scale": 1}},
        {"name": "CustomToolBar",   "config": {"toolbar_name": "customToolBar2"}},
        {"name": "Spacer",          "config": {"scale": 1}},
        {"name": "WindowControl",   "config": {"button_width": 60, "close_hover_bg": "#E81123"}}
    ]
}
```

Every entry needs a `name`; `config` is optional and unknown / invalid
values fall back to the component's defaults. An unknown `name`, a
malformed `config`, or invalid JSON makes the loader overwrite the file
with the template above — so a typo costs you your custom layout.

#### Built-in components

| Component | Purpose | Config keys |
|-----------|---------|-------------|
| `CurrentFileName` | Shows the active document name, or `Untitled` when none is open | `poll_ms` (int, default 500) |
| `OriginalMenuBar` | Migrated native QMenuBar | `compact` (bool, default false) — single icon button with dropdown; `menu_label` (str) — button text override |
| `Separator` | Fixed-width visual divider | `width` (int, px, default 8) |
| `Spacer` | Expands to fill remaining space | `scale` (int, ≥1, default 1) — proportion relative to other spacers |
| `ToolSlot` | **Photoshop-style tool slot** — click activates its tool, double-click / right-click swaps it | `tools` (**required**, list of Krita tool ids); `id` (str, persistence key); `size` (int, px); `poll_ms` (int, default 66); `show_marker` (bool, default true); `tooltip_hint` (str) |
| `CustomToolBar` | **Embeds a Krita QToolBar inside the titlebar** | `toolbar_name` (str, default `"customToolBar2"`) — objectName of any Krita toolbar |
| `WindowControl` | Minimize / Maximize / Close buttons | `button_width` (int, px, default 60), `close_hover_bg` (CSS color, default `"#E81123"`) |

#### Tool slots (`ToolSlot`)

One `ToolSlot` entry is one button backed by a list of tools. Nothing is
grouped behind the scenes — put several `ToolSlot` entries next to each
other and you get a Photoshop-like stack (a row, since the titlebar is
horizontal).

- The slot **remembers** which tool of its list it holds. First tool of
  the list is the initial one.
- **Single click** activates the remembered tool.
- **Double click** or **right click** opens a menu at the mouse cursor
  listing every tool of the slot; picking one activates it and becomes
  the tool the slot holds from then on. (A double click therefore also
  activates the remembered tool first — accepted behaviour.)
- **A slot holding a single tool** behaves like a plain tool button: no
  menu, and no corner marker.
- The slot **highlights** whenever the active tool belongs to its list,
  and shows that tool's icon. So switching tools with a keyboard shortcut
  updates the matching slot, Photoshop-style.
- The small corner triangle marks slots that hide more than one tool
  (`show_marker: false` removes it).
- The choice is persisted in Krita's own config (`kritarc`, group
  `[frameless]`, key `toolslot/<id>`), so it survives restarts and never
  touches `config.json`.

Krita exposes no "tool changed" signal to Python, so every slot polls the
active tool every `poll_ms` (66 ms by default).

**Finding tool ids.** Tool ids are the `objectName()` of the buttons in
Krita's own toolbox, e.g. `KritaShape/KisToolBrush`, `KritaFill/KisToolFill`,
`KisToolSelectOutline`, `SvgTextTool`. To list them, paste this into
Krita's Scripter (Tools → Scripts → Scripter):

```python
from PyQt5.QtWidgets import QToolButton
from krita import Krita

win = Krita.instance().activeWindow().qwindow()
for obj in win.findChildren(object):
    if obj.metaObject().className() == 'KoToolBox':
        for btn in obj.findChildren(QToolButton):
            if btn.objectName():
                print(repr(btn.objectName()), '|', btn.text())
```

Two slots with the same `tools` list share their memory unless you give
each an explicit `id`; when you reorder or edit a list, set `id` to keep
the previously remembered tool.

#### Adding your own component

1. Create `components/your_component.py` exposing
   `create(window, bar_h, config, ctx) -> QWidget`.
2. Register it in `COMPONENT_REGISTRY` in `components/__init__.py`.
3. Use `{"name": "YourComponent", "config": {...}}` in `config.json`.

Inside `create` you can subscribe to `ctx.palette_changed`,
`ctx.window_state_changed` and `ctx.teardown`. Always free timers,
event filters and shortcuts from the `teardown` handler — the titlebar is
destroyed and rebuilt whenever the window is reopened.

## Technical overview

### Why not `Qt.FramelessWindowHint`

The obvious approach is to call `QMainWindow.setWindowFlags(Qt.FramelessWindowHint)`, but on Windows this changes the underlying HWND to `WS_POPUP` style — which means Windows **stops sending `WM_NCHITTEST` entirely**. Without `WM_NCHITTEST` there is no way to provide resize cursors at window edges or implement edge-drag resizing.

### The correct approach: manual Win32 style manipulation

Our implementation is equivalent to how VS Code / Chrome / Electron handle custom titlebars at the lowest level:

| Step | What | Why |
|------|------|-----|
| 1. Win32 style | Remove `WS_CAPTION` (titlebar), keep `WS_THICKFRAME` (borders) | `WS_THICKFRAME` present → Windows still sends `WM_NCHITTEST` → resize + Aero Snap work |
| 2. DWM frame extension | `DwmExtendFrameIntoClientArea(0, 1, 0, 0)` | Tells the Desktop Window Manager "custom chrome in use" → DWM renders drop shadows |
| 3. `WM_NCCALCSIZE` | Return 0 → client rect = window rect | `WS_THICKFRAME` borders become invisible (0 px wide); window appears borderless |
| 4. `WM_NCHITTEST` | Return `HTLEFT` / `HTRIGHT` etc. for the outer 6 px | Windows shows the correct resize cursor and handles edge-dragging natively |
| 5. `WM_GETMINMAXINFO` | Set max bounds to monitor work area (excluding taskbar) | Maximised window does not cover the taskbar |

`WM_NCHITTEST` returns `False` / `0` while the window is maximised, so
the invisible resize border cannot steal clicks from a maximised window.

### Drag handling

A Qt `mousePressEvent` / `mouseMoveEvent` handler on the custom `_TitleBar` widget starts a window drag on **MouseMove after a 5 px threshold** (not on MousePress — this preserves double-click detection). The drag itself uses Qt's `QWindow.startSystemMove()`, which internally issues `DefWindowProc(WM_SYSCOMMAND, SC_MOVE | HTCAPTION)` — Aero Snap is triggered automatically.

A click is treated as interactive (never starts a drag) when the deepest
child under the cursor is a `QToolButton` — that covers the window
control buttons, the compact-mode menu button and every `ToolSlot`.

### Titlebar architecture

The custom titlebar is set as a **TopLeftCorner widget** of the original (cleared) QMenuBar, with a Resize event filter forcing it to full menubar width. Before clearing, all QMenu objects are extracted and migrated into a real `QMenuBar` widget inside the titlebar — preserving Alt+letter shortcuts, hover-to-switch, and keyboard navigation.

Because the titlebar is a child of the menubar, the menubar is given the
same minimum height — otherwise components taller than the (now empty)
menubar, such as the default 32 px `ToolSlot`, would be clipped.

Two guards keep that position alive: a 100 ms poll re-installs the corner
widget (and hides any TopRightCorner one) if Krita's MDI area steals it,
and `windowClosed` tears everything down — event filters removed, native
event filter uninstalled, components notified via `teardown`.

Components communicate with the titlebar via a shared `_ComponentContext`
(signal bus): `palette_changed`, `window_state_changed`, `teardown`.

### Krita-specific caveats

Krita's Python API objects (`Window`, `View`, `Document`, etc.) are **ephemeral thin wrappers** — they can be garbage-collected at any time. Never capture their references in signal callbacks or asynchronous code; cache stable identifiers such as `qwin.objectName()` and re-look-up the wrapper through `Krita.instance().windows()` when you need it. Menubar mutations are deferred via `QTimer.singleShot(0)` to avoid segfaults, while the Win32 / DWM style changes are applied synchronously so the window never flashes a native titlebar.

Note that `Document.fileName()` returns the **full path**, not the basename.

### File structure

```
frameless/
├── frameless.desktop                     # Krita plugin descriptor
├── frameless/
│   ├── __init__.py                       # Python package entry
│   ├── FramelessExtension.py             # main logic (Win32/DWM + titlebar + entry point)
│   ├── config.json                       # layout config (auto-generated on first run)
│   ├── components/
│   │   ├── __init__.py                   # component registry + config loader
│   │   ├── filename.py                   # CurrentFileName
│   │   ├── menubar.py                    # OriginalMenuBar
│   │   ├── separator.py                  # Separator (fixed-width divider)
│   │   ├── spacer.py                     # Spacer (proportional expansion)
│   │   ├── tool_slot.py                  # ToolSlot (Photoshop-style tool slot)
│   │   ├── tool_source.py                # tool lookup / activation helpers
│   │   ├── toolbar.py                    # CustomToolBar
│   │   └── window_control.py             # WindowControl
│   ├── krita.pyi                         # Krita Python API type stubs
│   └── Manual.html                       # Krita plugin help page
├── image.png                             # screenshot
├── README.md                             # this file (English)
└── README_cn.md                          # Chinese version
```
