"""Player view wrapping the video player component."""
from typing import Optional, Callable, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta

from ..services.state_manager import StateManager
from ..models.channel import Channel
from ..qt_components.video_player import VideoPlayerComponent


class PlayerView(QWidget):
    """Full-screen player view."""

    def __init__(self, state_manager: StateManager,
                 on_back: Optional[Callable] = None,
                 on_settings_click: Optional[Callable] = None,
                 parent=None):
        super().__init__(parent)
        self._state = state_manager
        self._on_back = on_back
        self._on_settings_click = on_settings_click
        self._episode_list: List[Channel] = []

        self._setup_ui()
        self._video_player.error.connect(self._on_video_error)
        self._video_player.next_requested.connect(self._on_next)
        self._video_player.prev_requested.connect(self._on_prev)

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
        back_btn.clicked.connect(lambda: self.handle_back())
        h_layout.addWidget(back_btn)

        self._name_label = QLabel("Select a channel")
        self._name_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        h_layout.addWidget(self._name_label)

        h_layout.addStretch()

        self._fav_btn = QToolButton()
        self._fav_icon_on  = qta.icon("mdi.heart",         color="#f472b6")
        self._fav_icon_off = qta.icon("mdi.heart-outline",  color="#7b90b8")
        self._fav_btn.setIcon(self._fav_icon_off)
        self._fav_btn.setIconSize(QSize(20, 20))
        self._fav_btn.setFixedSize(QSize(36, 36))
        self._fav_btn.setToolTip("Add to favourites")
        self._fav_btn.clicked.connect(self._toggle_favorite)
        h_layout.addWidget(self._fav_btn)

        prev_btn = QToolButton()
        prev_btn.setIcon(qta.icon("mdi.skip-previous", color="#7b90b8"))
        prev_btn.setIconSize(QSize(20, 20))
        prev_btn.setFixedSize(QSize(36, 36))
        prev_btn.clicked.connect(self._on_prev)
        h_layout.addWidget(prev_btn)

        next_btn = QToolButton()
        next_btn.setIcon(qta.icon("mdi.skip-next", color="#7b90b8"))
        next_btn.setIconSize(QSize(20, 20))
        next_btn.setFixedSize(QSize(36, 36))
        next_btn.clicked.connect(self._on_next)
        h_layout.addWidget(next_btn)

        layout.addWidget(header)

        # Video player
        self._video_player = VideoPlayerComponent(self)
        layout.addWidget(self._video_player, 1)

    def refresh(self):
        current = self._state.get_current_channel()
        if current:
            self._name_label.setText(current.name)
            self._update_fav_btn(current)

    def handle_back(self):
        self._video_player.stop()
        if self._on_back:
            self._on_back()

    def play_channel(self, channel: Channel):
        self._state.set_current_channel(channel)
        self._state.add_to_recently_viewed(channel)
        self._name_label.setText(channel.name)
        self._update_fav_btn(channel)

        saved = self._state.get_playback_position(channel.url)
        if saved and getattr(channel, "content_type", "live") != "live":
            self._video_player.set_resume_position(saved.get("position_ms", 0))
        else:
            self._video_player.set_resume_position(0)

        self._video_player.play_channel(channel)

    def _toggle_favorite(self):
        current = self._state.get_current_channel()
        if current:
            is_fav = self._state.toggle_favorite(current)
            self._fav_btn.setIcon(self._fav_icon_on if is_fav else self._fav_icon_off)
            self._fav_btn.setToolTip("Remove from favourites" if is_fav else "Add to favourites")

    def _update_fav_btn(self, channel: Channel):
        is_fav = self._state.is_favorite(channel)
        self._fav_btn.setIcon(self._fav_icon_on if is_fav else self._fav_icon_off)
        self._fav_btn.setToolTip("Remove from favourites" if is_fav else "Add to favourites")

    def _on_video_error(self, msg: str):
        # Errors are shown inside the video component
        pass

    def _on_next(self):
        self._navigate(1)

    def _on_prev(self):
        self._navigate(-1)

    def _navigate(self, delta: int):
        current = self._state.get_current_channel()
        if not current:
            return
        media_list = self._episode_list if self._episode_list else self._state.get_all_channels()
        if not media_list:
            return
        try:
            idx = next(i for i, ch in enumerate(media_list) if ch.url == current.url)
            new_idx = (idx + delta) % len(media_list)
            self.play_channel(media_list[new_idx])
        except StopIteration:
            pass

    def set_episode_context(self, episodes: List[Channel]):
        self._episode_list = episodes

    def show_loading(self, message: str = "Loading..."):
        # Loading is shown by the video component buffering overlay
        pass

    def hide_loading(self):
        pass

    def stop(self):
        self._video_player.stop()

    def toggle_play(self):
        self._video_player.toggle_play()

    def seek_relative(self, ms: int):
        self._video_player.seek_relative(ms)

    def adjust_volume(self, delta: int):
        self._video_player.adjust_volume(delta)

    def toggle_mute(self):
        self._video_player.toggle_mute()
