"""Content view with category sidebar and channel list."""
from typing import Optional, Callable, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QFrame,
    QSizePolicy, QSplitter, QComboBox, QToolButton,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap, QFont
import qtawesome as qta

from ..services.state_manager import StateManager
from ..models.channel import Channel


def _language_name(code: str) -> str:
    """Convert ISO-639-1/2 language code to readable name."""
    names = {
        "en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish",
        "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
        "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "hi": "Hindi",
        "tr": "Turkish", "nl": "Dutch", "pl": "Polish", "sv": "Swedish",
        "da": "Danish", "no": "Norwegian", "fi": "Finnish", "el": "Greek",
        "he": "Hebrew", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
        "cs": "Czech", "hu": "Hungarian", "ro": "Romanian", "sk": "Slovak",
        "uk": "Ukrainian", "bg": "Bulgarian", "hr": "Croatian", "sr": "Serbian",
        "sl": "Slovenian", "lt": "Lithuanian", "lv": "Latvian", "et": "Estonian",
    }
    return names.get(code.lower(), code) if code else "Unknown"


class ContentView(QWidget):
    """Content view with categories and virtualized channel list."""

    PAGE_SIZE = 50

    def __init__(self, state_manager: StateManager,
                 content_type: str = "live",
                 on_channel_select: Optional[Callable[[Channel], None]] = None,
                 on_back: Optional[Callable] = None,
                 on_settings_click: Optional[Callable] = None,
                 parent=None):
        super().__init__(parent)
        self.state = state_manager
        self.content_type = content_type
        self._on_channel_select = on_channel_select
        self._on_back = on_back
        self._on_settings_click = on_settings_click

        self._selected_category = "All"
        self._search_query = ""
        self._show_favorites_only = False
        self._channels: List[Channel] = []
        self._filtered: List[Channel] = []
        self._displayed_count = 0
        self._is_updating = False

        # Real-time search debounce
        self._search_debounce = QTimer()
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(250)
        self._search_debounce.timeout.connect(self._apply_filters)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("viewHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 10, 16, 10)

        back_btn = QPushButton("  Back")
        back_btn.setIcon(qta.icon("mdi.arrow-left", color="#a855f7"))
        back_btn.setIconSize(QSize(18, 18))
        back_btn.clicked.connect(lambda: self._on_back() if self._on_back else None)
        h_layout.addWidget(back_btn)

        self._title_label = QLabel("Live TV")
        self._title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        h_layout.addWidget(self._title_label)
        h_layout.addStretch()

        self._count_label = QLabel("0 items")
        self._count_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        h_layout.addWidget(self._count_label)
        layout.addWidget(header)

        # Body
        body = QHBoxLayout()
        body.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("viewSidebar")
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(10, 10, 10, 10)

        cat_title = QLabel("Categories")
        cat_title.setStyleSheet("font-weight: 700; font-size: 13px; margin-bottom: 4px;")
        s_layout.addWidget(cat_title)

        self._category_list = QListWidget()
        self._category_list.setStyleSheet("background: transparent;")
        self._category_list.itemClicked.connect(self._on_category_clicked)
        s_layout.addWidget(self._category_list)
        body.addWidget(sidebar)

        # Main area
        main = QWidget()
        m_layout = QVBoxLayout(main)
        m_layout.setContentsMargins(16, 16, 16, 16)
        m_layout.setSpacing(12)

        # Search + filters
        filter_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search channels across all categories...")
        self._search_edit.textChanged.connect(self._on_search_text_changed)
        filter_row.addWidget(self._search_edit, 1)

        self._fav_btn = QPushButton("  Favorites")
        self._fav_btn.setIcon(qta.icon("mdi.heart-outline", color="#f472b6"))
        self._fav_btn.setIconSize(QSize(16, 16))
        self._fav_btn.setCheckable(True)
        self._fav_btn.clicked.connect(self._toggle_favorites)
        filter_row.addWidget(self._fav_btn)
        m_layout.addLayout(filter_row)

        # Playlist filter
        self._playlist_combo = QComboBox()
        self._playlist_combo.addItem("All Playlists")
        self._playlist_combo.currentTextChanged.connect(self._on_playlist_changed)
        m_layout.addWidget(self._playlist_combo)

        # Channel list
        self._channel_list = QListWidget()
        self._channel_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._channel_list.setSpacing(4)
        self._channel_list.itemClicked.connect(self._on_channel_clicked)
        m_layout.addWidget(self._channel_list, 1)

        # Load more
        self._load_more_btn = QPushButton("Load More")
        self._load_more_btn.clicked.connect(self._load_more)
        self._load_more_btn.setVisible(False)
        m_layout.addWidget(self._load_more_btn)

        body.addWidget(main, 1)
        layout.addLayout(body, 1)

    def set_content_type(self, content_type: str):
        self.content_type = content_type
        titles = {"live": "Live TV", "movie": "Movies", "series": "TV Series"}
        self._title_label.setText(titles.get(content_type, "Content"))
        self._load_channels()

    def _load_channels(self):
        self._channels = self.state.get_channels_by_type(self.content_type)
        self._playlist_combo.clear()
        self._playlist_combo.addItem("All Playlists")
        for pl in self.state.get_playlists():
            self._playlist_combo.addItem(pl.name)
        self._refresh_categories()
        self._apply_filters()

    def _refresh_categories(self):
        self._category_list.clear()
        self._category_list.addItem("All")
        groups = set()
        for ch in self._channels:
            groups.add(ch.group)
        for g in sorted(groups)[:50]:
            self._category_list.addItem(g)

    def _on_category_clicked(self, item: QListWidgetItem):
        self._selected_category = item.text()
        self._apply_filters()

    def _on_playlist_changed(self, text: str):
        self._channels = self.state.get_channels_by_type(self.content_type, text if text != "All Playlists" else None)
        self._refresh_categories()
        self._apply_filters()

    def _toggle_favorites(self, checked: bool):
        self._show_favorites_only = checked
        self._fav_btn.setIcon(qta.icon("mdi.heart" if checked else "mdi.heart-outline", color="#f472b6"))
        self._apply_filters()

    def _on_search_text_changed(self, text: str):
        self._search_debounce.stop()
        self._search_debounce.start()

    def _apply_filters(self):
        if self._is_updating:
            return
        self._is_updating = True

        self._search_query = self._search_edit.text().strip().lower()
        self._filtered = list(self._channels)

        if self._show_favorites_only:
            self._filtered = [c for c in self._filtered if c.is_favorite]

        if self._search_query:
            # Search across ALL categories regardless of selected category
            self._filtered = [
                c for c in self._filtered
                if self._search_query in c.name.lower()
                or self._search_query in c.group.lower()
            ]
        elif self._selected_category != "All":
            self._filtered = [c for c in self._filtered if c.group == self._selected_category]

        self._channel_list.clear()
        self._displayed_count = 0
        self._load_batch(0, min(self.PAGE_SIZE, len(self._filtered)))

        total = len(self._filtered)
        if self._search_query:
            self._count_label.setText(f"{total} results")
        elif self._selected_category != "All":
            self._count_label.setText(f"{total} in {self._selected_category}")
        else:
            self._count_label.setText(f"{total} items")
        self._load_more_btn.setVisible(self._displayed_count < total)

        self._is_updating = False

    def _load_batch(self, start: int, end: int):
        for i in range(start, end):
            ch = self._filtered[i]
            # Build display text based on context
            if self._search_query:
                # Searching across all categories — show group badge
                text = f"{ch.name}\n📁 {ch.group}"
            elif self._selected_category != "All":
                # Already filtered to one category — no need to repeat the group
                text = ch.name
            else:
                # "All" view — show name + group for visual grouping
                text = f"{ch.name}\n{ch.group}"
            item = QListWidgetItem(text)
            if ch.is_favorite:
                item.setIcon(qta.icon("mdi.heart", color="#f472b6"))
            item.setData(Qt.UserRole, ch)
            item.setSizeHint(QSize(0, 64))
            self._channel_list.addItem(item)
        self._displayed_count = end

    def _load_more(self):
        start = self._displayed_count
        end = min(start + self.PAGE_SIZE, len(self._filtered))
        self._load_batch(start, end)
        self._load_more_btn.setVisible(self._displayed_count < len(self._filtered))

    def _on_channel_clicked(self, item: QListWidgetItem):
        ch = item.data(Qt.UserRole)
        if ch and self._on_channel_select:
            self._on_channel_select(ch)

    def capture_state(self) -> dict:
        return {
            "content_type": self.content_type,
            "search": self._search_edit.text(),
            "category": self._selected_category,
            "favorites": self._show_favorites_only,
            "playlist": self._playlist_combo.currentText(),
        }

    def restore_state(self, state: Optional[dict]):
        if not state:
            return
        self.content_type = state.get("content_type", "live")
        self._search_edit.setText(state.get("search", ""))
        self._selected_category = state.get("category", "All")
        self._show_favorites_only = state.get("favorites", False)
        self._fav_btn.setChecked(self._show_favorites_only)
        self._fav_btn.setText("♥ Favorites" if self._show_favorites_only else "♡ Favorites")
        self.set_content_type(self.content_type)
