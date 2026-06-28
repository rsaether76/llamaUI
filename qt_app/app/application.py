"""QApplication bootstrap, environment hints, and global configuration.

This module owns the lifecycle of the single QApplication. Constructing it is
separated from constructing the main window so future entry points (CLI mode,
tests) can reuse the configured application object.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from . import theme


def _configure_platform() -> None:
    """Detect the display session and set Qt platform hints.

    On X11 sessions (including Cinnamon, MATE, XFCE, KDE X11), force the
    xcb platform plugin to prevent Qt from accidentally selecting Wayland
    if ``WAYLAND_DISPLAY`` happens to be set (e.g. from XWayland or a
    previous Wayland session).  This avoids input/rendering bugs that
    PySide6 exhibits when running xcb-only desktops under the Wayland
    plugin.

    On genuine Wayland sessions, leave the default so Qt picks Wayland.
    If the user has already set ``QT_QPA_PLATFORM``, we respect that.
    """
    if os.environ.get("QT_QPA_PLATFORM"):
        return  # user override — do not touch

    # Heuristic: if XDG_SESSION_TYPE is x11, or DISPLAY is set but
    # WAYLAND_DISPLAY is not, we are almost certainly on X11.
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    has_display = bool(os.environ.get("DISPLAY"))
    has_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))

    if session_type == "x11" or (has_display and not has_wayland):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def _configure_hidpi() -> None:
    """Set HiDPI scaling hints appropriate for the detected platform.

    On X11, ``QT_AUTO_SCREEN_SCALE_FACTOR`` can cause Qt to pick a DPI
    that disagrees with the desktop's settings (especially Cinnamon),
    leading to blurry or oversized widgets.  We only enable the
    auto-scaling env vars on Wayland where they are needed.
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    is_wayland = session_type == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))

    if is_wayland:
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    # On X11, let Qt use the screen's reported DPI without overrides.


# Run platform detection early, before QApplication is created.
_configure_platform()
_configure_hidpi()


def _should_force_software_rendering() -> bool:
    """On NVIDIA + Wayland, QSG_RHI_BACKEND=software is a known safe fallback.

    The product is QWidget-only, so QSG is not used directly. This is a
    defensive hook for Qt internals (QQuickWidget etc. that some Qt
    submodules bring in). It does not affect rendering of QWidget windows.
    """
    return os.environ.get("QT_QUICK_BACKEND") == "software"


def create_app(argv: Optional[list[str]] = None) -> QApplication:
    """Create the singleton QApplication with theme and high-DPI configured."""
    if argv is None:
        argv = sys.argv

    app = QApplication.instance() or QApplication(argv)

    app.setApplicationName("llamaUI")
    app.setApplicationDisplayName("llamaUI")
    app.setOrganizationName("llamaUI")
    app.setOrganizationDomain("llamaUI.local")
    app.setDesktopFileName("llamaui")

    # Application icon — use the bundled PNG at the largest available size.
    _icons_dir = Path(__file__).resolve().parent.parent / "icons"
    if _icons_dir.is_dir():
        from PySide6.QtGui import QIcon
        icon = QIcon()
        for p in sorted(_icons_dir.glob("llamaui-*.png")):
            icon.addFile(str(p))
        app.setWindowIcon(icon)

    # KDE Wayland + NVIDIA hint: keep the EGL/GBM path the platform picks.
    # The PySide6 default Wayland plugin renders QWidget windows directly
    # to the surface.  On X11/Cinnamon this is irrelevant — the xcb plugin
    # is used instead (see _configure_platform).
    theme.apply_palette(app)
    app.setStyleSheet(theme.build_stylesheet())

    return app
