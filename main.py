#!/usr/bin/env python3
"""IPTV Player - A cross-platform IPTV player built with PySide6."""
import sys
import asyncio
from pathlib import Path
import qasync
from PySide6.QtWidgets import QApplication
from src.qt_app import IPTVMainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set window icon from bundled asset
    icon_path = Path(__file__).parent / "assets" / "logo.png"
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))

    from src.theme import apply_theme, watch_theme_changes
    apply_theme(app)
    watch_theme_changes(app)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = IPTVMainWindow()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
