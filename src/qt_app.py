"""Main application window with QStackedWidget navigation."""
import asyncio
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QKeySequence, QFont, QIcon, QShortcut

from .services.state_manager import StateManager
from .qt_views.hub_view import HubView
from .qt_views.content_view import ContentView
from .qt_views.player_view import PlayerView
from .qt_views.series_view import SeriesView
from .qt_views.settings_view import SettingsView
from .models.channel import Channel


class IPTVMainWindow(QMainWindow):
    """Main application window managing all views."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV Player")
        self.setMinimumSize(1000, 640)
        self.resize(1280, 720)

        self.state = StateManager()
        self._nav_stack: list[str] = []
        self._current_view = "hub"
        self._content_type = "live"
        self._view_before_player: Optional[str] = None
        self._window_geo_before_player: Optional[bytes] = None
        self._content_state_before_player: Optional[dict] = None

        self._setup_ui()
        self._setup_shortcuts()
        self._show_hub()

        QTimer.singleShot(200, self._initial_load)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._hub_view = HubView(
            state_manager=self.state,
            on_hub_select=self._on_hub_select,
            on_settings_click=self._show_settings,
            on_play_channel=self._on_channel_select,
        )
        self._content_view = ContentView(
            state_manager=self.state,
            on_channel_select=self._on_channel_select,
            on_back=self._go_back,
            on_settings_click=self._show_settings,
        )
        self._player_view = PlayerView(
            state_manager=self.state,
            on_back=self._go_back,
            on_settings_click=self._show_settings,
        )
        self._settings_view = SettingsView(
            state_manager=self.state,
            on_back=self._go_back,
        )
        self._series_view = SeriesView(
            state_manager=self.state,
            on_back=self._go_back,
            on_play_episode=self._play_series_episode,
        )

        self._stack.addWidget(self._hub_view)
        self._stack.addWidget(self._content_view)
        self._stack.addWidget(self._player_view)
        self._stack.addWidget(self._settings_view)
        self._stack.addWidget(self._series_view)

        self._view_map = {
            "hub": self._hub_view,
            "content": self._content_view,
            "player": self._player_view,
            "settings": self._settings_view,
            "series": self._series_view,
        }
        self._name_map = {v: k for k, v in self._view_map.items()}

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Esc"), self, activated=self._on_escape)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self._show_hub)
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)
        QShortcut(QKeySequence("Space"), self, activated=self._shortcut_play_pause)
        QShortcut(QKeySequence("Left"), self, activated=self._shortcut_seek_back)
        QShortcut(QKeySequence("Right"), self, activated=self._shortcut_seek_forward)
        QShortcut(QKeySequence("Up"), self, activated=self._shortcut_vol_up)
        QShortcut(QKeySequence("Down"), self, activated=self._shortcut_vol_down)
        QShortcut(QKeySequence("M"), self, activated=self._shortcut_mute)

    def _on_escape(self):
        if self._current_view == "player":
            self._player_view.handle_back()
        elif self._current_view != "hub":
            self._go_back()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _shortcut_play_pause(self):
        if self._current_view == "player":
            self._player_view.toggle_play()

    def _shortcut_seek_back(self):
        if self._current_view == "player":
            self._player_view.seek_relative(-10000)   # 10 s backward

    def _shortcut_seek_forward(self):
        if self._current_view == "player":
            self._player_view.seek_relative(10000)     # 10 s forward

    def _shortcut_vol_up(self):
        if self._current_view == "player":
            self._player_view.adjust_volume(5)

    def _shortcut_vol_down(self):
        if self._current_view == "player":
            self._player_view.adjust_volume(-5)

    def _shortcut_mute(self):
        if self._current_view == "player":
            self._player_view.toggle_mute()

    def _show_view(self, name: str):
        widget = self._view_map.get(name)
        if widget:
            self._stack.setCurrentWidget(widget)
            self._current_view = name

    def _show_hub(self):
        self._nav_stack.clear()
        self._current_view = "hub"
        self._hub_view.refresh()
        self._show_view("hub")

    def _show_content(self, content_type: str):
        self._nav_stack.append(self._current_view)
        self._current_view = "content"
        self._content_type = content_type
        self._content_view.set_content_type(content_type)
        self._show_view("content")

    def _show_player(self):
        self._view_before_player = self._current_view
        self._window_geo_before_player = self.saveGeometry()
        if self._current_view == "content":
            self._content_state_before_player = self._content_view.capture_state()
        self._nav_stack.append(self._current_view)
        self._current_view = "player"
        self._player_view.refresh()
        self._show_view("player")

    def _show_series(self, series_name: str, episodes: list):
        self._nav_stack.append(self._current_view)
        self._current_view = "series"
        self._series_view.load_series(series_name, episodes)
        self._show_view("series")

    def _show_settings(self):
        self._nav_stack.append(self._current_view)
        self._current_view = "settings"
        self._show_view("settings")

    def _go_back(self):
        if self._current_view == "player":
            if self._window_geo_before_player:
                self.restoreGeometry(self._window_geo_before_player)
            self._player_view.stop()

        if self._nav_stack:
            prev = self._nav_stack.pop()
            if prev == "hub":
                self._show_hub()
            elif prev == "content":
                self._current_view = "content"
                if self._content_state_before_player:
                    self._content_view.restore_state(self._content_state_before_player)
                    self._content_state_before_player = None
                self._show_view("content")
            elif prev == "player":
                self._current_view = "player"
                self._player_view.refresh()
                self._show_view("player")
            elif prev == "series":
                self._current_view = "series"
                self._show_view("series")
            elif prev == "settings":
                self._current_view = "settings"
                self._show_view("settings")
            else:
                self._show_hub()
        elif self._view_before_player and self._view_before_player != "player":
            prev = self._view_before_player
            self._view_before_player = None
            if prev == "content":
                self._current_view = "content"
                self._show_view("content")
            elif prev == "series":
                self._current_view = "series"
                self._show_view("series")
            elif prev == "settings":
                self._current_view = "settings"
                self._show_view("settings")
            else:
                self._show_hub()
        else:
            self._show_hub()

    def _on_hub_select(self, hub_id: str):
        if hub_id == "settings":
            self._show_settings()
        elif hub_id in ("live", "movie", "series"):
            self._show_content(hub_id)

    def _on_channel_select(self, channel: Channel):
        if getattr(channel, "content_type", "") == "series":
            if getattr(channel, "url", "").startswith("xtream://series/"):
                asyncio.create_task(self._load_xtream_series(channel))
                return
            elif getattr(channel, "series_name", ""):
                episodes = self.state.get_series_episodes(channel.series_name)
                if episodes:
                    self._show_series(channel.name, episodes)
                    return
        self._player_view.set_episode_context([])
        self._show_player()
        self._player_view.play_channel(channel)

    async def _load_xtream_series(self, channel: Channel):
        from .services.xtream_client import XtreamCodesClient, XtreamCredentials

        self._player_view.show_loading("Loading series...")
        try:
            playlist = self.state.get_playlist_for_channel(channel)
            if not playlist or not playlist.metadata:
                raise Exception("Playlist or credentials not found")

            metadata = dict(playlist.metadata or {})
            if not metadata.get("password"):
                server = metadata.get("server", "")
                username = metadata.get("username", "")
                for provider in self.state.get_xtream_providers():
                    if provider.get("server") == server and provider.get("username") == username:
                        metadata["password"] = provider.get("password", "")
                        break

            if not metadata.get("password"):
                raise Exception("Missing Xtream credentials")

            creds = XtreamCredentials.from_dict(metadata)
            client = XtreamCodesClient(creds)
            data = await client.get_series_info(channel.series_id)

            all_eps = []
            if isinstance(data, list):
                all_eps = data
            elif isinstance(data, dict):
                episodes_data = data.get("episodes", {})
                if isinstance(episodes_data, dict):
                    for season_eps in episodes_data.values():
                        if isinstance(season_eps, list):
                            all_eps.extend(season_eps)
                elif isinstance(episodes_data, list):
                    all_eps = episodes_data

            episodes = []
            for ep in all_eps:
                if not isinstance(ep, dict):
                    continue
                ep_id = str(ep.get("id", ""))
                ext = ep.get("container_extension", "mp4")
                url = client.build_series_episode_url(ep_id, ext)
                ep_info = ep.get("info", {}) if isinstance(ep.get("info"), dict) else {}
                episodes.append(Channel(
                    name=ep.get("title", f"Episode {ep.get('episode_num')}"),
                    url=url,
                    logo=ep_info.get("movie_image", "") or channel.logo,
                    group=channel.group,
                    content_type="series",
                    series_name=channel.name,
                    season=int(ep.get("season", 1) or 1),
                    episode=int(ep.get("episode_num", 0) or 0),
                ))

            self._show_series(channel.name, episodes)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load series: {e}")
        finally:
            self._player_view.hide_loading()

    def _play_series_episode(self, channel: Channel):
        episodes = self._series_view.episodes()
        self._player_view.set_episode_context(episodes)
        self._show_player()
        self._player_view.play_channel(channel)

    def _initial_load(self):
        self._hub_view.refresh()
