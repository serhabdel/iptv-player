"""Series view with seasons and episodes."""
from typing import Optional, Callable, List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QSplitter, QFrame,
)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta

from ..services.state_manager import StateManager
from ..models.channel import Channel


class SeriesView(QWidget):
    """View for series seasons and episodes."""

    def __init__(self, state_manager: StateManager,
                 on_back: Optional[Callable] = None,
                 on_play_episode: Optional[Callable[[Channel], None]] = None,
                 parent=None):
        super().__init__(parent)
        self.state = state_manager
        self._on_back = on_back
        self._on_play_episode = on_play_episode
        self._series_name: str = ""
        self._episodes: List[Channel] = []
        self._seasons: Dict[int, List[Channel]] = {}
        self._sorted_seasons: List[int] = []

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
        self._title_label = QLabel("Series")
        self._title_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        h_layout.addWidget(self._title_label)
        h_layout.addStretch()
        layout.addWidget(header)

        # Info row
        info = QWidget()
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(16, 16, 16, 16)
        self._poster_label = QLabel("📺")
        self._poster_label.setFixedSize(120, 170)
        self._poster_label.setObjectName("posterPlaceholder")
        self._poster_label.setStyleSheet("font-size: 48px;")
        self._poster_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._poster_label)

        meta = QVBoxLayout()
        self._meta_name = QLabel("")
        self._meta_name.setStyleSheet("font-size: 24px; font-weight: 700;")
        meta.addWidget(self._meta_name)
        self._meta_count = QLabel("")
        self._meta_count.setStyleSheet("font-size: 13px;")
        meta.addWidget(self._meta_count)
        meta.addSpacing(8)
        self._play_first_btn = QPushButton("▶  Play S1 E1")
        self._play_first_btn.setObjectName("primary")
        self._play_first_btn.clicked.connect(self._play_first)
        meta.addWidget(self._play_first_btn)
        meta.addStretch()
        info_layout.addLayout(meta, 1)
        layout.addWidget(info)

        # Season selector
        season_row = QHBoxLayout()
        season_row.setContentsMargins(16, 12, 16, 8)
        season_lbl = QLabel("Season:")
        season_lbl.setStyleSheet("font-weight: 600;")
        season_row.addWidget(season_lbl)
        self._season_combo = QComboBox()
        self._season_combo.currentIndexChanged.connect(self._on_season_change)
        season_row.addWidget(self._season_combo)
        season_row.addStretch()
        layout.addLayout(season_row)

        # Episode list
        self._episode_list = QListWidget()
        self._episode_list.setSpacing(4)
        self._episode_list.itemClicked.connect(self._on_episode_clicked)
        layout.addWidget(self._episode_list, 1)

    def load_series(self, series_name: str, episodes: List[Channel]):
        self._series_name = series_name
        self._episodes = episodes
        self._title_label.setText(series_name)
        self._meta_name.setText(series_name)

        # Group by season
        self._seasons = {}
        unknown = []
        for ep in episodes:
            if ep.season:
                self._seasons.setdefault(ep.season, []).append(ep)
            else:
                unknown.append(ep)
        if unknown:
            if not self._seasons:
                self._seasons[1] = unknown
            else:
                self._seasons[0] = unknown

        self._sorted_seasons = sorted(self._seasons.keys())
        self._season_combo.clear()
        for s in self._sorted_seasons:
            label = f"Season {s}" if s > 0 else "Extras"
            self._season_combo.addItem(label, s)

        self._meta_count.setText(f"{len(self._seasons)} Season(s)  •  {len(episodes)} Episode(s)")
        self._update_episode_list()

    def _update_episode_list(self):
        self._episode_list.clear()
        season = self._season_combo.currentData()
        eps = self._seasons.get(season, [])
        eps.sort(key=lambda x: x.episode if x.episode else 999)
        for ep in eps:
            label = f"S{ep.season:02d}E{ep.episode:02d}  •  {ep.name}" if ep.season and ep.episode else ep.name
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ep)
            item.setSizeHint(QSize(0, 52))
            self._episode_list.addItem(item)

    def _on_season_change(self, index: int):
        self._update_episode_list()

    def _on_episode_clicked(self, item: QListWidgetItem):
        ep = item.data(Qt.UserRole)
        if ep and self._on_play_episode:
            self._on_play_episode(ep)

    def _play_first(self):
        if not self._sorted_seasons:
            return
        first_season = self._seasons.get(self._sorted_seasons[0], [])
        if first_season:
            first_season.sort(key=lambda x: x.episode if x.episode else 999)
            if self._on_play_episode:
                self._on_play_episode(first_season[0])

    def episodes(self) -> List[Channel]:
        return self._episodes
