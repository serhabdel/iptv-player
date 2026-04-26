"""Hub view with responsive card grid and modern layout."""
from typing import Optional, Callable, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QScrollArea, QSizePolicy, QProgressBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap
import qtawesome as qta

from ..services.state_manager import StateManager
from ..models.channel import Channel


class HubCard(QWidget):
    """Clickable hub card with icon, title, and count."""

    clicked = None  # assigned externally

    def __init__(self, hub_id: str, title: str, subtitle: str, count: int,
                 icon_name: str, gradient: str, glow: str, parent=None):
        super().__init__(parent)
        self.hub_id = hub_id
        self.setMinimumSize(240, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(160)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            HubCard {{
                background: {gradient};
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            HubCard:hover {{
                border: 2px solid {glow};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(6)

        top = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="white").pixmap(QSize(36, 36)))
        icon_lbl.setStyleSheet("background: transparent;")
        top.addWidget(icon_lbl)
        top.addStretch()
        if count is not None:
            count_lbl = QLabel(f"{count:,}")
            count_lbl.setStyleSheet(
                "font-size: 20px; font-weight: 800; color: white;"
                "background: rgba(0,0,0,0.28); padding: 4px 12px;"
                "border-radius: 10px;"
            )
            top.addWidget(count_lbl)
        layout.addLayout(top)
        layout.addStretch()

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: white; background: transparent;"
        )
        layout.addWidget(title_lbl)

        sub = QLabel(subtitle)
        sub.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.75); background: transparent;")
        layout.addWidget(sub)

    def mousePressEvent(self, event):
        if self.clicked:
            self.clicked(self.hub_id)


class ResponsiveCardGrid(QWidget):
    """Widget that holds cards in a responsive grid layout."""

    def __init__(self, min_card_width: int = 260, spacing: int = 20, parent=None):
        super().__init__(parent)
        self._min_card_width = min_card_width
        self._spacing = spacing
        self._cards: List[HubCard] = []
        self._layout = QGridLayout(self)
        self._layout.setSpacing(spacing)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(Qt.AlignTop)

    def set_cards(self, cards: List[HubCard]):
        # Remove old cards
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._cards = list(cards)
        self._reflow()

    def _reflow(self):
        # Clear grid
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        # Recalculate columns based on available width
        avail = self.width() - 20  # small padding margin
        cols = max(1, avail // (self._min_card_width + self._spacing))
        for i, card in enumerate(self._cards):
            self._layout.addWidget(card, i // cols, i % cols)
        # Stretch last row to fill
        for c in range(cols):
            self._layout.setColumnStretch(c, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()


class ContinueWatchingCard(QWidget):
    """Rich card for Continue Watching with thumbnail, progress bar, and metadata."""

    clicked = None  # assigned externally

    _TYPE_GRADIENTS = {
        "movie":  "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #be185d,stop:1 #ec4899)",
        "series": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0d9488,stop:1 #14b8a6)",
        "live":   "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #4f46e5,stop:1 #a855f7)",
    }
    _TYPE_ICONS = {
        "movie":  "mdi.movie-open",
        "series": "mdi.television-box",
        "live":   "mdi.broadcast",
    }

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedSize(200, 260)
        self.setCursor(Qt.PointingHandCursor)

        content_type = item.get("content_type", "movie")
        grad = self._TYPE_GRADIENTS.get(content_type, self._TYPE_GRADIENTS["movie"])
        icon_name = self._TYPE_ICONS.get(content_type, self._TYPE_ICONS["movie"])
        progress = item.get("progress", 0)
        name = item.get("name", "Unknown")
        group = item.get("group", "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Thumbnail area ──
        thumb = QWidget()
        thumb.setFixedHeight(140)
        thumb.setStyleSheet(f"""
            QWidget {{
                background: {grad};
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }}
        """)
        t_layout = QVBoxLayout(thumb)
        t_layout.setAlignment(Qt.AlignCenter)

        play_icon = QLabel()
        play_icon.setPixmap(qta.icon("mdi.play-circle", color="rgba(255,255,255,0.9)").pixmap(QSize(48, 48)))
        play_icon.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(play_icon)

        # Type badge
        if group:
            badge = QLabel(group[:18])
            badge.setStyleSheet(
                "background: rgba(0,0,0,0.45); color: white; padding: 2px 8px;"
                "border-radius: 6px; font-size: 10px; font-weight: 600;"
            )
            badge.setAlignment(Qt.AlignCenter)
            t_layout.addWidget(badge, alignment=Qt.AlignCenter)

        layout.addWidget(thumb)

        # ── Info area ──
        info = QWidget()
        info.setStyleSheet("""
            QWidget {
                background: #1e1e2e;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
        """)
        i_layout = QVBoxLayout(info)
        i_layout.setContentsMargins(12, 10, 12, 12)
        i_layout.setSpacing(6)

        title = QLabel(name[:22] + "…" if len(name) > 22 else name)
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #e2e8f0;")
        title.setWordWrap(True)
        i_layout.addWidget(title)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(int(progress))
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background: #334155;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #38bdf8, stop:1 #a855f7);
                border-radius: 2px;
            }
        """)
        i_layout.addWidget(self._progress_bar)

        resume = QLabel(f"Resume at {int(progress)}%")
        resume.setStyleSheet("font-size: 11px; color: #94a3b8;")
        i_layout.addWidget(resume)

        layout.addWidget(info)

        # Hover border effect via parent stylesheet
        self.setStyleSheet("""
            ContinueWatchingCard {
                background: transparent;
                border-radius: 14px;
            }
            ContinueWatchingCard:hover {
                border: 2px solid #a855f7;
            }
        """)

    def mousePressEvent(self, event):
        if self.clicked:
            self.clicked(self.item)


class HubView(QWidget):
    """Main hub navigation view."""

    def __init__(self, state_manager: StateManager,
                 on_hub_select: Optional[Callable[[str], None]] = None,
                 on_settings_click: Optional[Callable] = None,
                 on_play_channel: Optional[Callable[[Channel], None]] = None,
                 parent=None):
        super().__init__(parent)
        self.state = state_manager
        self._on_hub_select = on_hub_select
        self._on_settings_click = on_settings_click
        self._on_play_channel = on_play_channel

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        layout.addWidget(scroll, 1)

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(40, 32, 40, 32)
        c_layout.setSpacing(28)
        scroll.setWidget(container)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(12)
        logo_icon = QLabel()
        logo_icon.setPixmap(qta.icon("mdi.television-play", color="#a855f7").pixmap(QSize(32, 32)))
        header.addWidget(logo_icon)
        logo = QLabel("IPTV Player")
        logo.setStyleSheet("font-size: 26px; font-weight: 800; letter-spacing: -0.5px;")
        header.addWidget(logo)
        header.addStretch()
        settings_btn = QPushButton("  Settings")
        settings_btn.setIcon(qta.icon("mdi.cog-outline", color="#a855f7"))
        settings_btn.setIconSize(QSize(18, 18))
        settings_btn.clicked.connect(lambda: self._on_hub_select("settings") if self._on_hub_select else None)
        header.addWidget(settings_btn)
        c_layout.addLayout(header)

        # ── Hero banner ──
        hero = QWidget()
        hero.setMinimumHeight(140)
        hero.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #4f46e544, stop:0.4 #7c3aed33, stop:1 #a855f722);
                border-radius: 20px;
                border: 1px solid rgba(168,85,247,0.25);
            }
        """)
        h_layout = QHBoxLayout(hero)
        h_layout.setContentsMargins(28, 20, 28, 20)
        h_text = QVBoxLayout()
        welcome = QLabel("Welcome Back!")
        welcome.setStyleSheet("font-size: 22px; font-weight: 700;")
        h_text.addWidget(welcome)
        subtitle = QLabel("Pick up where you left off or explore something new.")
        subtitle.setStyleSheet("font-size: 13px; opacity: 0.75;")
        h_text.addWidget(subtitle)
        h_layout.addLayout(h_text)
        h_layout.addStretch()
        c_layout.addWidget(hero)

        # ── Cards section ──
        cards_title = QHBoxLayout()
        explore_icon = QLabel()
        explore_icon.setPixmap(qta.icon("mdi.compass-outline", color="#a855f7").pixmap(QSize(18, 18)))
        cards_title.addWidget(explore_icon)
        explore_lbl = QLabel("Explore")
        explore_lbl.setStyleSheet("font-size: 16px; font-weight: 700; padding-left: 6px;")
        cards_title.addWidget(explore_lbl)
        cards_title.addStretch()
        c_layout.addLayout(cards_title)

        counts = self.state.get_content_counts()

        card_defs = [
            ("live",  "Live TV",  "Live Channels", counts.get("live", 0),
             "mdi.broadcast",
             "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #4f46e5,stop:0.5 #7c3aed,stop:1 #a855f7)",
             "#c084fc"),
            ("movie", "Movies",   "Films & VOD",   counts.get("movie", 0),
             "mdi.movie-open",
             "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #be185d,stop:0.5 #ec4899,stop:1 #fb7185)",
             "#fda4af"),
            ("series","Series",   "TV Shows",      counts.get("series", 0),
             "mdi.television-box",
             "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0d9488,stop:0.5 #14b8a6,stop:1 #4ade80)",
             "#86efac"),
            ("settings","Settings","Configure",    None,
             "mdi.tune-vertical",
             "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1d4ed8,stop:0.5 #3b82f6,stop:1 #38bdf8)",
             "#7dd3fc"),
        ]

        self._card_grid = ResponsiveCardGrid(min_card_width=260, spacing=18)
        cards = []
        for hid, title, sub, count, icon, grad, glow in card_defs:
            card = HubCard(hid, title, sub, count, icon, grad, glow)
            card.clicked = self._on_hub_select
            cards.append(card)
        self._card_grid.set_cards(cards)
        c_layout.addWidget(self._card_grid)

        # ── Continue Watching ──
        recent_header = QHBoxLayout()
        recent_icon = QLabel()
        recent_icon.setPixmap(qta.icon("mdi.history", color="#a855f7").pixmap(QSize(18, 18)))
        recent_header.addWidget(recent_icon)
        self._recent_label = QLabel("Continue Watching")
        self._recent_label.setStyleSheet(
            "font-size: 15px; font-weight: 700; padding-left: 6px;"
        )
        recent_header.addWidget(self._recent_label)
        recent_header.addStretch()
        c_layout.addLayout(recent_header)

        self._recent_list = QWidget()
        self._recent_layout = QHBoxLayout(self._recent_list)
        self._recent_layout.setSpacing(12)
        self._recent_layout.setAlignment(Qt.AlignLeft)
        self._recent_layout.addStretch()
        c_layout.addWidget(self._recent_list)

        c_layout.addStretch()

    def refresh(self):
        self._refresh_recent()

    def _refresh_recent(self):
        # Clear recent layout (keep the stretch at the end)
        while self._recent_layout.count() > 1:
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent = self.state.get_continue_watching(limit=10)
        if not recent:
            self._recent_label.setVisible(False)
            self._recent_list.setVisible(False)
            return

        self._recent_label.setVisible(True)
        self._recent_list.setVisible(True)

        for item in recent:
            card = ContinueWatchingCard(item)
            card.clicked = self._play_recent
            # Insert before the final stretch
            self._recent_layout.insertWidget(self._recent_layout.count() - 1, card)

    def _play_recent(self, item: dict):
        if self._on_play_channel:
            ch = Channel(
                name=item.get("name", "Unknown"),
                url=item.get("url", ""),
                logo=item.get("logo", ""),
                group=item.get("group", ""),
                content_type=item.get("content_type", "movie"),
            )
            self._on_play_channel(ch)
