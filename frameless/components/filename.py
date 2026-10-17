"""CurrentFileName — shows the active Krita document name.

* no document open           → the label hides (nothing to show)
* document open, never saved → shows ``Untitled``
* document open, saved       → shows the file path
* unsaved changes            → a ``*`` is appended (same meaning as the ``*``
  Krita itself puts in the window title)
"""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QLabel, QSizePolicy
from krita import Krita


DEFAULT_POLL_MS = 200
PLACEHOLDER_TEXT = "Untitled"
MODIFIED_MARKER = "*"


class _FileNameSection(QLabel):
    """Polls Krita for the active document name."""

    def __init__(self, bar_h: int, poll_ms: int = DEFAULT_POLL_MS,
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(bar_h)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(poll_ms)

    def _refresh(self):
        try:
            doc = Krita.instance().activeDocument()
            if doc is None:
                self.hide()
                return
            fname = doc.fileName()
            # Document.modified() is the public libkis mirror of
            # KisDocument::isModified(): true while the undo stack is not at a
            # saved state. getattr keeps old Krita builds from breaking the
            # whole component.
            modified = bool(getattr(doc, 'modified', lambda: False)())
        except Exception:
            self.hide()
            return
        text = fname if fname else PLACEHOLDER_TEXT
        if modified:
            text += MODIFIED_MARKER
        if text != self.text():
            self.setText(text)
            self.setToolTip(fname if fname else PLACEHOLDER_TEXT)
        self.show()

    def teardown(self):
        self._timer.stop()


def create(window, bar_h: int, config: dict, ctx):
    """Factory: CurrentFileName component.

    config keys (all optional):
        poll_ms: int — polling interval in ms (default 200)
    """
    poll_ms = config.get('poll_ms', DEFAULT_POLL_MS)
    if not isinstance(poll_ms, int) or poll_ms <= 0:
        poll_ms = DEFAULT_POLL_MS

    widget = _FileNameSection(bar_h, poll_ms)
    ctx.teardown.connect(widget.teardown)
    return widget
