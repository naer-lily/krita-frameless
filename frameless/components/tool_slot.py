"""ToolSlot — a Photoshop-style tool slot for the frameless titlebar.

One slot is one button backed by a list of Krita tools:

* the slot *remembers* which tool of its list it shows (persisted in
  Krita's kritarc, group ``frameless``, key ``toolslot/<id>``);
* a single left click activates that remembered tool;
* double click or right click pops up a menu at the mouse cursor; picking
  an entry activates it *and* becomes the tool the slot shows from then
  on.  A slot holding a single tool never shows that menu;
* the slot highlights itself whenever the active tool belongs to its list,
  and in that case also shows that tool's icon — Photoshop's behaviour, so
  switching tools with a keyboard shortcut updates the matching slot.

A double click therefore activates the remembered tool first and pops the
menu right after; that is accepted behaviour.
"""

from __future__ import annotations

import hashlib
import traceback
from typing import List, Optional

from PyQt5.QtCore import QPoint, QSize, Qt, QTimer
from PyQt5.QtGui import (
    QCursor, QKeySequence, QPainter, QPalette, QPolygon,
)
from PyQt5.QtWidgets import (
    QApplication, QMenu, QSizePolicy, QToolButton, QWidget,
)
from krita import Krita

from .tool_source import ToolSource


SETTINGS_GROUP = "frameless"
DEFAULT_POLL_MS = 66
DEFAULT_BAR_H = 28
DEFAULT_SIZE = 32
MARKER_SIZE = 5

_STYLESHEET = """
QToolButton {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}
QToolButton:hover {
    background: palette(mid);
}
QToolButton:checked {
    background: palette(highlight);
}
"""


# ---------------------------------------------------------------------------
# Empty placeholder (invalid / empty `tools` config)
# ---------------------------------------------------------------------------

class _EmptySlot(QWidget):
    """Fixed-size, disabled placeholder so a broken config cannot collapse
    the titlebar layout."""

    def __init__(self, bar_h: int, parent=None):
        super().__init__(parent)
        side = bar_h if bar_h > 0 else DEFAULT_BAR_H
        self.setFixedSize(side, side)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setToolTip("ToolSlot: 'tools' is empty or invalid")


# ---------------------------------------------------------------------------
# The slot button
# ---------------------------------------------------------------------------

class _ToolSlotButton(QToolButton):
    """A single tool slot.  Must stay a direct QToolButton subclass so the
    titlebar's ``_is_interactive_child()`` treats it as interactive and
    never starts a window drag from it."""

    def __init__(self, window, bar_h: int, tools: List[str], slot_id: str,
                 poll_ms: int, config: dict):
        super().__init__()
        self._tools = tools
        self._slot_id = slot_id
        self._poll_ms = poll_ms
        self._source = ToolSource(window.qwindow())
        self._show_marker = bool(config.get("show_marker", True))
        self._tooltip_hint = str(config.get("tooltip_hint") or "")
        self._remembered = self._load_remembered()
        self._saved = self._remembered
        self._shown: Optional[str] = None
        self._menu: Optional[QMenu] = None

        bar_h = bar_h if bar_h > 0 else DEFAULT_BAR_H
        side = config.get("size")
        if not isinstance(side, int) or isinstance(side, bool) or side <= 0:
            side = max(bar_h, DEFAULT_SIZE)

        self.setFixedSize(side, max(bar_h, side))
        icon_side = max(16, side - 8)
        self.setIconSize(QSize(icon_side, icon_side))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setAutoRaise(True)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet(_STYLESHEET)

        self.clicked.connect(self._on_clicked)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._sync)
        self._apply_display(force=True)

    # -- persistence ------------------------------------------------------

    def _setting_name(self) -> str:
        return f"toolslot/{self._slot_id}"

    def _load_remembered(self) -> str:
        try:
            raw = Krita.instance().readSetting(
                SETTINGS_GROUP, self._setting_name(), "")
        except Exception:
            raw = ""
        if isinstance(raw, str) and raw in self._tools:
            return raw
        return self._tools[0]

    def _save_remembered(self):
        if self._remembered == self._saved:
            return
        try:
            Krita.instance().writeSetting(
                SETTINGS_GROUP, self._setting_name(), self._remembered)
            self._saved = self._remembered
        except Exception:
            pass

    # -- lifecycle --------------------------------------------------------

    def start(self):
        self._sync()
        self._timer.start(self._poll_ms)

    def teardown(self):
        self._timer.stop()
        if self._menu is not None:
            self._menu.close()
            self._menu = None
        self._source.invalidate()

    # -- state sync -------------------------------------------------------

    def _current_tool(self) -> Optional[str]:
        current = self._source.current_id()
        if current is None:
            # Toolbox closed/unavailable — fall back to the tool QActions.
            current = self._source.checked_among(self._tools)
        return current

    def _displayed_id(self) -> str:
        current = self._current_tool()
        if current and current in self._tools:
            return current
        return self._remembered

    def _sync(self):
        # Never let a slot failure escape into Qt's event loop.
        try:
            if Krita.instance().activeDocument() is None:
                # No document open — the titlebar section hides entirely.
                self.setVisible(False)
                return
            self.setVisible(True)

            current = self._current_tool()
            if current and current in self._tools:
                if current != self._remembered:
                    self._remembered = current
                    self._save_remembered()
            self.setChecked(bool(current and current in self._tools))
            self._apply_display()
        except Exception:
            traceback.print_exc()

    def _apply_display(self, force: bool = False):
        shown = self._displayed_id()
        if not force and shown == self._shown:
            return
        self._shown = shown
        info = self._source.info(shown)
        self.setIcon(info.icon)
        tip = info.label
        if info.shortcut:
            tip = f"{tip} ({info.shortcut})"
        if self._tooltip_hint:
            tip = f"{tip}\n{self._tooltip_hint}"
        self.setToolTip(tip)

    # -- interaction ------------------------------------------------------

    def _on_clicked(self):
        try:
            self._source.activate(self._remembered)
            self._sync()
        except Exception:
            traceback.print_exc()

    def _choose(self, tool_id: str):
        try:
            if not self._source.activate(tool_id):
                return
            self._remembered = tool_id
            self._save_remembered()
            self._sync()
            self._apply_display(force=True)
        except Exception:
            traceback.print_exc()

    def _build_menu(self) -> Optional[QMenu]:
        """The swap menu, or None when there is nothing to choose from."""
        # A single-tool slot has nothing to choose from.
        if len(self._tools) < 2:
            return None

        menu = QMenu(self)
        shown = self._displayed_id()
        current_action = None
        for tool_id in self._tools:
            info = self._source.info(tool_id)
            action = menu.addAction(info.icon, info.label)
            action.setCheckable(True)
            action.setChecked(tool_id == shown)
            if tool_id == shown:
                # The style's check indicator sits inside the icon cell and is
                # easy to miss, so mark the tool the slot holds in bold as
                # well and make it the menu's active row.
                current_action = action
                font = action.font()
                font.setBold(True)
                action.setFont(font)
            if info.shortcut:
                # Display only — the action is never added to a widget, so
                # this cannot grab a global shortcut.
                action.setShortcut(QKeySequence(info.shortcut))
            action.setData(tool_id)
            if not info.found:
                action.setText(f"{info.label}  (not found)")
                action.setEnabled(False)
            action.triggered.connect(
                lambda _checked=False, tid=tool_id: self._choose(tid))
        menu.setActiveAction(current_action)
        return menu

    def _show_menu(self):
        menu = self._build_menu()
        if menu is None:
            return

        self.setDown(False)
        self._menu = menu

        # Krita sets Qt::AA_DontShowIconsInMenus on non-KDE platforms
        # (krita/main.cc: "Icons in menus are ugly and distracting"), which
        # makes Qt drop every action icon — the swap menu would be text only.
        # Flip the flag for the lifetime of this one menu so the tools'
        # icons are previewed, then put it back.
        app = QApplication.instance()
        restore = (app is not None
                   and app.testAttribute(Qt.AA_DontShowIconsInMenus))
        if restore:
            app.setAttribute(Qt.AA_DontShowIconsInMenus, False)
        try:
            menu.exec_(QCursor.pos())
        finally:
            if restore:
                app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
            self._menu = None
        self._sync()
        self._apply_display(force=True)

    def contextMenuEvent(self, event):
        self._show_menu()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._show_menu()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # -- painting ---------------------------------------------------------

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._show_marker or len(self._tools) < 2:
            return
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            colour = self.palette().color(QPalette.ButtonText)
            colour.setAlpha(170)
            painter.setPen(Qt.NoPen)
            painter.setBrush(colour)
            w, h, s = self.width(), self.height(), MARKER_SIZE
            painter.drawPolygon(QPolygon([
                QPoint(w - s, h - 1),
                QPoint(w - 1, h - s),
                QPoint(w - 1, h - 1),
            ]))
            painter.end()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _parse_tools(config: dict) -> List[str]:
    tools = config.get("tools")
    if not isinstance(tools, list):
        print("[frameless.ToolSlot] 'tools' must be a list of Krita tool ids")
        return []
    cleaned: List[str] = []
    for item in tools:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
        else:
            print(f"[frameless.ToolSlot] ignoring invalid tool entry: {item!r}")
    if not cleaned:
        print("[frameless.ToolSlot] 'tools' is empty — slot disabled")
    return cleaned


def _slot_id(config: dict, tools: List[str]) -> str:
    raw = config.get("id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    digest = hashlib.md5(",".join(sorted(tools)).encode("utf-8")).hexdigest()
    return "auto-" + digest[:10]


def create(window, bar_h: int, config: dict, ctx):
    """Factory: ToolSlot component.

    config keys (all optional except ``tools``):
        tools: list[str]  — Krita tool ids, first one is the initial tool
        id: str           — persistence key (derived from tools when omitted)
        size: int         — button width in px (default: max(bar_h, 32))
        poll_ms: int      — active-tool polling interval (default 66)
        show_marker: bool — draw the hidden-tools corner marker (default True)
        tooltip_hint: str — extra line appended to the tooltip
    """
    tools = _parse_tools(config)
    if not tools:
        return _EmptySlot(bar_h)

    poll_ms = config.get("poll_ms", DEFAULT_POLL_MS)
    if not isinstance(poll_ms, int) or isinstance(poll_ms, bool) or poll_ms <= 0:
        poll_ms = DEFAULT_POLL_MS

    slot = _ToolSlotButton(
        window, bar_h, tools, _slot_id(config, tools), poll_ms, config)
    ctx.teardown.connect(slot.teardown)
    slot.start()
    return slot
