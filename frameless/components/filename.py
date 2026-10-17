"""CurrentFileName — shows the active Krita document name.

* no document open           → the label hides (nothing to show)
* document open, never saved → shows ``Untitled``
* document open, saved       → shows the file path
* unsaved changes            → a ``*`` is appended (same meaning as the ``*``
  Krita itself puts in the window title)
* ``show_edit_time``         → the time Krita has tracked for editing this
  document is appended as ``HH:MM:SS``

The editing time is read from the document's own info XML
(``<editing-time>`` in seconds, the very counter Krita's *Document
Information* dialog shows). Krita only bumps that counter in 30s/60s steps,
so it is polled on its own, much slower timer instead of the name poll.
"""
from xml.etree import ElementTree

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QLabel, QSizePolicy
from krita import Krita


DEFAULT_POLL_MS = 200
DEFAULT_EDIT_TIME_POLL_MS = 30000
PLACEHOLDER_TEXT = "Untitled"
MODIFIED_MARKER = "*"
EDITING_TIME_TAG = "editing-time"


def _format_seconds(total: int) -> str:
    total = max(0, int(total))
    return "%02d:%02d:%02d" % (total // 3600, total % 3600 // 60, total % 60)


def _document_edit_seconds(doc) -> int:
    """Editing time of *doc* in seconds, 0 when it cannot be read.

    ``Document.documentInfo()`` is the calligra document-info XML, i.e. the
    same place KiDocument keeps ``editing-time`` in. Unlike the reference
    implementation this never *writes* the info back: reading the label must
    not dirty the document.
    """
    try:
        xml = doc.documentInfo()
    except Exception:
        return 0
    if not xml:
        return 0
    try:
        root = ElementTree.fromstring(xml.encode("utf-8"))
    except Exception:
        return 0

    for elem in root.iter():
        tag = elem.tag
        if not isinstance(tag, str):
            continue
        # Namespaced documents: keep only the local name.
        if tag.rsplit("}", 1)[-1] != EDITING_TIME_TAG:
            continue
        raw = (elem.text or "").strip()
        try:
            return max(0, int(float(raw)))
        except (TypeError, ValueError):
            return 0
    return 0


class _FileNameSection(QLabel):
    """Polls Krita for the active document name (and optionally its time)."""

    def __init__(self, bar_h: int, poll_ms: int = DEFAULT_POLL_MS,
                 show_edit_time: bool = False,
                 edit_time_poll_ms: int = DEFAULT_EDIT_TIME_POLL_MS,
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(bar_h)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._show_edit_time = show_edit_time
        self._edit_seconds = 0
        self._last_name = None

        self._refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(poll_ms)

        # The editing time moves in 30s/60s steps inside Krita, so there is
        # nothing to gain from polling it as often as the name.
        self._edit_timer = None
        if show_edit_time:
            self._edit_timer = QTimer(self)
            self._edit_timer.timeout.connect(self._refresh_edit_time)
            self._edit_timer.start(edit_time_poll_ms)

    # -- polling ----------------------------------------------------------

    def _refresh_edit_time(self):
        try:
            doc = Krita.instance().activeDocument()
            self._edit_seconds = _document_edit_seconds(doc) if doc is not None else 0
        except Exception:
            self._edit_seconds = 0

    def _refresh(self):
        try:
            doc = Krita.instance().activeDocument()
            if doc is None:
                self._last_name = None
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

        name = fname if fname else PLACEHOLDER_TEXT
        if name != self._last_name:
            # Another document (or the first one): the editing time belongs to
            # the document, so refresh it now instead of waiting for the slow
            # timer.
            self._last_name = name
            if self._show_edit_time:
                self._refresh_edit_time()

        text = name + (MODIFIED_MARKER if modified else "")
        tip = name
        if self._show_edit_time:
            pretty = _format_seconds(self._edit_seconds)
            text = f"{text}  {pretty}"
            tip = f"{name}\nEditing time: {pretty}"

        if text != self.text():
            self.setText(text)
            self.setToolTip(tip)
        self.show()

    def teardown(self):
        self._timer.stop()
        if self._edit_timer is not None:
            self._edit_timer.stop()


def create(window, bar_h: int, config: dict, ctx):
    """Factory: CurrentFileName component.

    config keys (all optional):
        poll_ms: int            — name/star polling interval (default 200)
        show_edit_time: bool    — append the document's editing time
                                  (default False)
        edit_time_poll_ms: int  — how often that time is re-read
                                  (default 30000)
    """
    poll_ms = config.get('poll_ms', DEFAULT_POLL_MS)
    if not isinstance(poll_ms, int) or isinstance(poll_ms, bool) or poll_ms <= 0:
        poll_ms = DEFAULT_POLL_MS

    edit_time_poll_ms = config.get('edit_time_poll_ms', DEFAULT_EDIT_TIME_POLL_MS)
    if (not isinstance(edit_time_poll_ms, int)
            or isinstance(edit_time_poll_ms, bool)
            or edit_time_poll_ms <= 0):
        edit_time_poll_ms = DEFAULT_EDIT_TIME_POLL_MS

    widget = _FileNameSection(
        bar_h, poll_ms,
        show_edit_time=bool(config.get('show_edit_time', False)),
        edit_time_poll_ms=edit_time_poll_ms,
    )
    ctx.teardown.connect(widget.teardown)
    return widget
