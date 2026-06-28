"""Common base for stacked page widgets."""
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget


class PagePolicy(Enum):
    """Determines how the shell lays out the sidebar / inspector for a page.

    - STANDARD: three-column layout (sidebar | content | inspector).
    - INSPECTOR_OPTIONAL: three-column, inspector collapsed by default.
    - FULL_WIDTH: inspector hidden, content fills the space.
    """

    STANDARD = "standard"
    INSPECTOR_OPTIONAL = "inspector_optional"
    FULL_WIDTH = "full_width"


class _WheelPropagatorFilter(QObject):
    """Event filter that propagates wheel events to a parent QScrollArea.

    Installed on inner QScrollAreas (e.g. advanced-group tab containers)
    so that when the inner area reaches its scroll limit, the remaining
    wheel delta is forwarded to the outer page-level QScrollArea.

    Without this, wheel events are silently consumed by the inner area
    once it hits its boundary, and the outer page stops scrolling.
    """

    def __init__(self, target_scroll_area: QScrollArea, parent: QObject | None = None):
        super().__init__(parent)
        self._target = target_scroll_area

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Wheel:
            return super().eventFilter(obj, event)

        # Let the inner scroll area handle the event first by checking
        # whether it is at a boundary in the wheel direction.
        inner = obj if isinstance(obj, QScrollArea) else None
        if inner is None:
            return super().eventFilter(obj, event)

        sb = inner.verticalScrollBar()
        delta = event.angleDelta().y()
        at_top = delta > 0 and sb.value() == sb.minimum()
        at_bottom = delta < 0 and sb.value() == sb.maximum()

        if at_top or at_bottom:
            # Forward to the target (outer) scroll area.
            # Post a cloned wheel event so Qt delivers it normally.
            from PySide6.QtGui import QWheelEvent
            forwarded = QWheelEvent(
                event.position(),
                event.globalPosition(),
                event.pixelDelta(),
                event.angleDelta(),
                event.buttons(),
                event.modifiers(),
                event.phase(),
                event.inverted(),
                event.source(),
            )
            from PySide6.QtWidgets import QApplication
            QApplication.sendEvent(self._target.viewport(), forwarded)
            return True  # consume the original

        return super().eventFilter(obj, event)


def install_wheel_propagation(inner: QScrollArea, outer: QScrollArea) -> None:
    """Install wheel propagation from *inner* to *outer* scroll area.

    When the inner area is scrolled to its boundary, wheel events are
    forwarded to the outer area so the page continues scrolling.
    """
    inner.installEventFilter(_WheelPropagatorFilter(inner, inner))



class PageBase(QScrollArea):
    """A scrollable page that hosts dense, styled content.

    Subclasses populate the page by adding widgets to ``self._layout``
    inside :meth:`build` (called once from ``__init__``).
    """

    navigate_requested = Signal(str)  # emits NavItemId value string
    policy: PagePolicy = PagePolicy.STANDARD

    def __init__(self, parent=None):
        super().__init__(parent)
        # The scroll viewport takes the page styles; the QScrollArea itself
        # stays transparent so the shell background shows through gaps.
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._body = QWidget(self)
        self._body.setObjectName("PageBody")
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(20, 18, 20, 18)
        self._layout.setSpacing(14)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._body)

        self.build()

    def build(self) -> None:
        """Override to populate the page. Default: empty body."""
