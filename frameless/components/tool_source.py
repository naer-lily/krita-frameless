"""Krita tool introspection helpers for the ToolSlot component.

Krita's Python API exposes no "current tool" getter and no tool-changed
signal, so we inspect the window's ``KoToolBox`` the same way
``yuuki_krita_helper/MyToolbox.py`` does: the checked ``QToolButton``
inside it carries the active tool id in its ``objectName()``, and a tool
is activated by clicking the matching button.

The toolbox is looked up lazily and cached per window.  The cache is
dropped by ``invalidate()`` on teardown and retried once whenever a
cached C++ object raises ``RuntimeError`` — sip wrappers die with their
window, and a module-global cache that never expires (as in MyToolbox)
breaks after the window is recreated.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QToolButton
from krita import Krita


TOOLBOX_CLASS_NAME = "KoToolBox"
FALLBACK_ICON_NAME = "krita_tool_freehand"


class ToolInfo(NamedTuple):
    icon: QIcon
    label: str
    shortcut: str
    found: bool


# id(qwin) -> tool buttons found inside that window's KoToolBox
_BUTTON_CACHE: Dict[int, List[QToolButton]] = {}
# id(qwin) -> {tool_id: ToolInfo}; only resolved ids are cached
_INFO_CACHE: Dict[int, Dict[str, ToolInfo]] = {}


def _qaction(tool_id: str):
    """Krita's QAction for a tool id (e.g. ``KritaShape/KisToolBrush``)."""
    try:
        return Krita.instance().action(tool_id)
    except Exception:
        return None


class ToolSource:
    """Reads the active tool and activates tools for one Krita window."""

    def __init__(self, qwin):
        self._qwin = qwin
        self._key = id(qwin)

    # -- toolbox buttons --------------------------------------------------

    def _find_toolbox(self):
        try:
            for obj in self._qwin.findChildren(QObject):
                try:
                    if obj.metaObject().className() == TOOLBOX_CLASS_NAME:
                        return obj
                except RuntimeError:
                    continue
        except RuntimeError:
            pass

        # Second chance: a floating / detached toolbox lives in its own
        # top-level window, so it is not a child of the main window.
        try:
            for widget in QApplication.allWidgets():
                try:
                    if widget.metaObject().className() == TOOLBOX_CLASS_NAME:
                        return widget
                except RuntimeError:
                    continue
        except Exception:
            pass
        return None

    def _scan_buttons(self) -> List[QToolButton]:
        toolbox = self._find_toolbox()
        if toolbox is None:
            return []
        try:
            return [b for b in toolbox.findChildren(QToolButton)
                    if b.objectName()]
        except RuntimeError:
            return []

    def buttons(self) -> List[QToolButton]:
        cached = _BUTTON_CACHE.get(self._key)
        if cached:
            return cached
        found = self._scan_buttons()
        if found:
            _BUTTON_CACHE[self._key] = found
        return found

    def invalidate(self):
        _BUTTON_CACHE.pop(self._key, None)
        _INFO_CACHE.pop(self._key, None)

    # -- current tool -----------------------------------------------------

    def current_id(self) -> Optional[str]:
        """Active tool id, or None when it cannot be determined."""
        for _ in range(2):
            buttons = self.buttons()
            if not buttons:
                return None
            dead = False
            for btn in buttons:
                try:
                    if btn.isChecked():
                        return btn.objectName() or None
                except RuntimeError:
                    dead = True
                    break
            if not dead:
                return None
            self.invalidate()
        return None

    def checked_among(self, tool_ids) -> Optional[str]:
        """Fallback when the toolbox is unavailable: ask the tool QActions.

        Only the ids we care about are queried, so this stays cheap.
        """
        for tool_id in tool_ids:
            action = _qaction(tool_id)
            if action is None:
                continue
            try:
                if action.isChecked():
                    return tool_id
            except RuntimeError:
                continue
        return None

    # -- activation -------------------------------------------------------

    def activate(self, tool_id: str) -> bool:
        if not tool_id:
            return False
        for _ in range(2):
            dead = False
            for btn in self.buttons():
                try:
                    if btn.objectName() == tool_id:
                        btn.click()
                        return True
                except RuntimeError:
                    dead = True
                    break
            if not dead:
                break
            self.invalidate()

        # The toolbox may be closed/unavailable — trigger the action instead.
        action = _qaction(tool_id)
        if action is not None:
            try:
                action.trigger()
                return True
            except RuntimeError:
                pass
        return False

    # -- metadata ---------------------------------------------------------

    def info(self, tool_id: str) -> ToolInfo:
        cache = _INFO_CACHE.setdefault(self._key, {})
        hit = cache.get(tool_id)
        if hit is not None and hit.found:
            return hit
        info = self._build_info(tool_id)
        cache[tool_id] = info  # unresolved ids are rebuilt on next call
        return info

    def _build_info(self, tool_id: str) -> ToolInfo:
        icon = QIcon()
        label = tool_id
        shortcut = ""
        found = False

        action = _qaction(tool_id)
        if action is not None:
            try:
                text = action.text().replace("&", "").strip()
                label = text or tool_id
                shortcut = action.shortcut().toString()
                icon = action.icon()
                found = True
            except RuntimeError:
                pass

        # The toolbox button carries the icon Krita itself renders, so it
        # wins over the action's icon.
        for btn in self.buttons():
            try:
                if btn.objectName() != tool_id:
                    continue
                found = True
                if not btn.icon().isNull():
                    icon = btn.icon()
                if label == tool_id:
                    label = (btn.text() or btn.toolTip() or tool_id).strip()
                break
            except RuntimeError:
                break

        if icon.isNull():
            try:
                icon = Krita.instance().icon(FALLBACK_ICON_NAME)
            except Exception:
                pass

        return ToolInfo(icon=icon, label=label, shortcut=shortcut, found=found)
