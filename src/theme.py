"""Theme system with light/dark palettes and dynamic QSS generation."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette

DARK = {
    "bg":           "#080b14",
    "bg_widget":    "#0d1117",
    "bg_card":      "#141b2d",
    "bg_hover":     "#1c2640",
    "border":       "#2a3655",
    "text":         "#e8edf5",
    "text_muted":   "#7b90b8",
    "accent":       "#a855f7",
    "accent_light": "#d08cff",
    "accent_dark":  "#7c3aed",
    "accent2":      "#f472b6",
    "accent3":      "#38bdf8",
    "accent4":      "#34d399",
    "accent5":      "#fbbf24",
    "danger":       "#f87171",
    "success":      "#4ade80",
    # gradient endpoints for header/sidebar
    "grad_h1":      "#0d0f1e",
    "grad_h2":      "#12183a",
    "grad_s1":      "#0a0d1c",
    "grad_s2":      "#111830",
    "grad_ctrl1":   "#0c0f20",
    "grad_ctrl2":   "#141b2d",
}

LIGHT = {
    "bg":           "#f0f4ff",
    "bg_widget":    "#ffffff",
    "bg_card":      "#e8eeff",
    "bg_hover":     "#dce5ff",
    "border":       "#b8c9f5",
    "text":         "#0a0e1f",
    "text_muted":   "#5264a0",
    "accent":       "#7c3aed",
    "accent_light": "#a855f7",
    "accent_dark":  "#6d28d9",
    "accent2":      "#ec4899",
    "accent3":      "#0ea5e9",
    "accent4":      "#10b981",
    "accent5":      "#f59e0b",
    "danger":       "#ef4444",
    "success":      "#22c55e",
    "grad_h1":      "#eef2ff",
    "grad_h2":      "#e8e0ff",
    "grad_s1":      "#f5f7ff",
    "grad_s2":      "#ede9fe",
    "grad_ctrl1":   "#eef2ff",
    "grad_ctrl2":   "#e8e0ff",
}


def _build_qss(c: dict) -> str:
    return f"""
/* ── Base ─────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {c["bg"]};
    color: {c["text"]};
    font-family: "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
    font-size: 13px;
}}

/* ── Inputs ───────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c["bg_card"]};
    border: 1.5px solid {c["border"]};
    border-radius: 10px;
    padding: 8px 14px;
    color: {c["text"]};
    selection-background-color: {c["accent"]};
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 1.5px solid {c["accent"]};
    background-color: {c["bg_hover"]};
}}

/* ── Buttons ──────────────────────────────────────────── */
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {c["bg_hover"]}, stop:1 {c["bg_card"]});
    border: 1px solid {c["border"]};
    border-radius: 10px;
    padding: 7px 16px;
    color: {c["text"]};
    font-weight: 500;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["accent_dark"]}, stop:1 {c["accent"]});
    border-color: {c["accent_light"]};
    color: #ffffff;
}}
QPushButton:pressed {{
    background: {c["accent_dark"]};
    color: #ffffff;
}}
QPushButton#primary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["accent_dark"]}, stop:0.5 {c["accent"]}, stop:1 {c["accent2"]});
    border: none;
    color: #ffffff;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["accent"]}, stop:1 {c["accent2"]});
}}

/* ── ToolButtons ──────────────────────────────────────── */
QToolButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 5px;
    color: {c["text"]};
}}
QToolButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["accent_dark"]}55, stop:1 {c["accent"]}33);
    border: 1px solid {c["accent"]}55;
}}
QToolButton:pressed {{
    background: {c["accent"]}44;
}}

/* ── ComboBox ─────────────────────────────────────────── */
QComboBox {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {c["bg_hover"]}, stop:1 {c["bg_card"]});
    border: 1px solid {c["border"]};
    border-radius: 10px;
    padding: 6px 14px;
    color: {c["text"]};
}}
QComboBox:hover {{ border-color: {c["accent"]}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border"]};
    color: {c["text"]};
    selection-background-color: {c["accent"]};
    border-radius: 8px;
    padding: 4px;
}}

/* ── Lists ────────────────────────────────────────────── */
QListView, QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListView::item, QListWidget::item {{
    border-radius: 10px;
    padding: 9px 14px;
    margin: 2px 4px;
    color: {c["text"]};
}}
QListView::item:selected, QListWidget::item:selected {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["accent_dark"]}55, stop:1 {c["accent"]}33);
    color: {c["text"]};
    border: 1px solid {c["accent"]}88;
}}
QListView::item:hover, QListWidget::item:hover {{
    background: {c["bg_hover"]}88;
}}

/* ── Sliders ──────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 5px;
    background: {c["border"]};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,fx:0.5,fy:0.5,
        stop:0 #ffffff, stop:0.4 {c["accent_light"]}, stop:1 {c["accent"]});
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 1px solid {c["accent_dark"]};
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["accent3"]}, stop:0.5 {c["accent"]}, stop:1 {c["accent2"]});
    border-radius: 3px;
}}

/* ── Scrollbars ───────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    border-radius: 3px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {c["border"]};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {c["accent"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    border-radius: 3px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {c["border"]};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c["accent"]}; }}

/* ── Menus ────────────────────────────────────────────── */
QMenu {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border"]};
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{ padding: 7px 26px; border-radius: 7px; color: {c["text"]}; }}
QMenu::item:selected {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["accent_dark"]}, stop:1 {c["accent"]});
    color: #ffffff;
}}

/* ── Progress ─────────────────────────────────────────── */
QProgressBar {{
    background-color: {c["bg_card"]};
    border-radius: 4px;
    height: 4px;
    text-align: center;
    color: transparent;
    border: none;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["accent3"]}, stop:0.5 {c["accent"]}, stop:1 {c["accent2"]});
    border-radius: 4px;
}}

/* ── Labels ───────────────────────────────────────────── */
QLabel {{ color: {c["text"]}; }}
QLabel#muted {{ color: {c["text_muted"]}; }}

/* ── Dialogs ──────────────────────────────────────────── */
QDialog {{
    background-color: {c["bg"]};
    border: 1px solid {c["border"]};
    border-radius: 16px;
}}
QGroupBox {{
    border: 1.5px solid {c["border"]};
    border-radius: 12px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
    color: {c["text"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {c["accent"]};
}}

/* ── Tabs ─────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {c["border"]};
    border-radius: 12px;
    background: {c["bg"]};
    top: -1px;
}}
QTabBar::tab {{
    background: {c["bg_card"]};
    border: 1px solid {c["border"]};
    border-bottom: none;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    padding: 9px 22px;
    margin-right: 2px;
    color: {c["text_muted"]};
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["accent_dark"]}44, stop:1 {c["accent"]}22);
    color: {c["accent_light"]};
    border-color: {c["accent"]};
    font-weight: 700;
}}
QTabBar::tab:hover {{
    background: {c["bg_hover"]};
    color: {c["text"]};
}}

/* ── Named Widgets ────────────────────────────────────── */
QWidget#viewHeader {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["grad_h1"]}, stop:0.5 {c["grad_h2"]}, stop:1 {c["grad_h1"]});
    border-bottom: 1px solid {c["border"]};
}}
QWidget#viewSidebar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["grad_s1"]}, stop:1 {c["grad_s2"]});
    border-right: 1px solid {c["border"]};
}}
QWidget#infoBar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["grad_h1"]}, stop:1 {c["grad_h2"]});
    border-bottom: 1px solid {c["border"]};
}}
QWidget#controlBar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["grad_ctrl1"]}, stop:1 {c["grad_ctrl2"]});
    border-top: 1px solid {c["border"]};
}}
QWidget#seekBar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c["grad_ctrl1"]}, stop:1 {c["grad_ctrl2"]});
}}
QPushButton#recentCard {{
    text-align: left;
    padding: 10px 14px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["bg_widget"]}, stop:1 {c["bg_card"]});
    border: 1px solid {c["border"]};
    border-radius: 10px;
    color: {c["text"]};
    font-size: 13px;
}}
QPushButton#recentCard:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["accent_dark"]}44, stop:1 {c["accent"]}22);
    border-color: {c["accent"]};
    color: {c["accent_light"]};
}}
QWidget#posterPlaceholder {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c["bg_card"]}, stop:1 {c["bg_hover"]});
    border-radius: 12px;
    border: 1px solid {c["border"]};
}}
QWidget#welcomeOverlay, QWidget#bufferOverlay, QWidget#errorOverlay {{
    background-color: rgba(0,0,0,0.88);
    border-radius: 0px;
}}
"""


def detect_theme(app: QApplication) -> bool:
    """Returns True if system prefers dark mode."""
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Unknown:
        bg = app.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128
    return scheme == Qt.ColorScheme.Dark


def apply_theme(app: QApplication):
    """Apply light or dark theme based on system preference."""
    is_dark = detect_theme(app)
    colors = DARK if is_dark else LIGHT
    app.setStyleSheet(_build_qss(colors))


def watch_theme_changes(app: QApplication):
    """Connect to system theme changes and reapply stylesheet."""
    app.styleHints().colorSchemeChanged.connect(lambda scheme: apply_theme(app))
