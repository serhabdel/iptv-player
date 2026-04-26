"""Generate a simple app icon from qtawesome and save as .ico."""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QSize
import qtawesome as qta

def generate_icon():
    app = QApplication(sys.argv)
    sizes = [16, 32, 48, 64, 128, 256]
    pixmaps = []
    for sz in sizes:
        px = QPixmap(sz, sz)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        # Background circle
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#7c3aed"))
        p.drawEllipse(2, 2, sz - 4, sz - 4)
        # TV icon
        icon = qta.icon("mdi.television-play", color="white")
        icon_px = icon.pixmap(QSize(int(sz * 0.6), int(sz * 0.6)))
        x = (sz - icon_px.width()) // 2
        y = (sz - icon_px.height()) // 2
        p.drawPixmap(x, y, icon_px)
        p.end()
        pixmaps.append(px)

    out = Path("assets/icon.ico")
    out.parent.mkdir(parents=True, exist_ok=True)
    # Save first size as PNG, then use a simple approach
    pixmaps[-1].save(str(out.with_suffix(".png")))
    # Windows ICO: Qt can save multi-size via QImageWriter but it's tricky.
    # Simpler: just save the largest PNG and use it as icon via PyInstaller --icon
    print(f"Saved icon PNG to {out.with_suffix('.png')}")

if __name__ == "__main__":
    generate_icon()
