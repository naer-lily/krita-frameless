"""CustomToolBar — hosts a Krita QToolBar inside the titlebar.

Qt limitation: `layout.addWidget()` unavoidably reparents the toolbar to this
widget.  The original parent is saved and restored on teardown.

Krita hides every toolbar when the last document closes
(``KisMainWindow::adjustLayoutForWelcomePage()``) and brings them back
through ``QMainWindow::restoreState()`` when a document is reopened.  A
toolbar that we reparented into the titlebar is no longer in the window's
toolbar area, so ``restoreState()`` never shows it again and it stays
hidden for the rest of the session.

``_sync_document_state()`` repairs exactly that: on a no-document →
document transition it re-shows the toolbar (and re-hosts it if Krita
managed to re-dock it elsewhere).  It only reacts to that transition, so a
toolbar the user hid by hand stays hidden.
"""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QToolBar, QVBoxLayout, QSizePolicy
from krita import Krita


# How often the document state is polled.  Krita only flips it when a
# document opens or closes, so this can be lazy.
DOC_SYNC_MS = 200
# Extra ticks to keep re-asserting visibility after a document reopens, in
# case Krita's layout restore runs a moment later and hides it again.
REASSERT_TICKS = 5


class _ToolBarSection(QWidget):
    """Zero-margin widget that hosts a named QToolBar in its layout."""

    def __init__(self, window, bar_h: int, config: dict, parent=None):
        super().__init__(parent)
        qwin = window.qwindow()
        toolbar_name = config.get('toolbar_name', 'customToolBar2')
        self._toolbar: QToolBar | None = qwin.findChild(QToolBar, toolbar_name)
        self._original_parent = None
        self._had_document = self._document_open()
        self._reassert = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._toolbar is not None:
            self._original_parent = self._toolbar.parent()
            # ⚠ layout.addWidget() will reparent the toolbar to self.
            # This is unavoidable in Qt.
            layout.addWidget(self._toolbar)
            # Krita hides toolbars while the welcome page is up; respect that
            # instead of forcing the toolbar visible on a document-less window.
            if self._had_document:
                self._toolbar.show()
            else:
                self._toolbar.hide()

        # Let the toolbar dictate the size — no fixed height
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._sync_document_state)
        self._sync_timer.start(DOC_SYNC_MS)

    # -- document state ---------------------------------------------------

    @staticmethod
    def _document_open() -> bool:
        try:
            return Krita.instance().activeDocument() is not None
        except Exception:
            return False

    def _host_toolbar(self):
        """Make sure the toolbar still lives in our layout, then show it."""
        if self._toolbar is None:
            return
        try:
            if self._toolbar.parent() is not self:
                # Krita's layout restore may have re-docked it elsewhere.
                self.layout().addWidget(self._toolbar)
            self._toolbar.show()
        except RuntimeError:
            self._toolbar = None

    def _sync_document_state(self):
        if self._toolbar is None:
            return
        has_document = self._document_open()

        if has_document == self._had_document:
            if self._reassert > 0:
                self._reassert -= 1
                if has_document:
                    self._host_toolbar()
            return

        self._had_document = has_document
        if has_document:
            self._host_toolbar()
            self._reassert = REASSERT_TICKS
        else:
            try:
                self._toolbar.hide()
            except RuntimeError:
                self._toolbar = None
            self._reassert = 0

    # -- teardown ---------------------------------------------------------

    def teardown(self):
        """Remove toolbar from layout and restore it to its original parent."""
        self._sync_timer.stop()
        if self._toolbar is None:
            return
        try:
            self.layout().removeWidget(self._toolbar)
            if self._original_parent is not None:
                self._toolbar.setParent(self._original_parent)
        except: pass 
        self._toolbar = None


def create(window, bar_h: int, config: dict, ctx):
    """Factory: CustomToolBar.

    Finds the named QToolBar via findChild, then hosts it in a zero-margin
    QVBoxLayout.  The toolbar is reparented to the returned widget (Qt
    requirement); original parent is restored on teardown.

    config keys (all optional):
        toolbar_name: str -- objectName of the QToolBar to find
                      (default 'customToolBar2')
    """
    widget = _ToolBarSection(window, bar_h, config)
    ctx.teardown.connect(widget.teardown)
    return widget
