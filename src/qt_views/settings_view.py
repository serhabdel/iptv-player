"""Settings view for playlist and provider management."""
import asyncio
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QTabWidget, QFormLayout, QGroupBox,
)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta

from ..services.state_manager import StateManager
from ..services.m3u_parser import M3UParser
from ..services.xtream_client import XtreamCodesClient, XtreamCredentials


class SettingsView(QWidget):
    """Settings view with playlist and provider management."""

    def __init__(self, state_manager: StateManager,
                 on_back: Optional[Callable] = None,
                 parent=None):
        super().__init__(parent)
        self._state = state_manager
        self._on_back = on_back
        self._setup_ui()
        self._refresh_lists()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header = QWidget()
        header.setObjectName("viewHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        back_btn = QPushButton("  Back")
        back_btn.setIcon(qta.icon("mdi.arrow-left", color="#a855f7"))
        back_btn.setIconSize(QSize(18, 18))
        back_btn.clicked.connect(lambda: self._on_back() if self._on_back else None)
        header_layout.addWidget(back_btn)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addWidget(header)

        tabs = QTabWidget()

        # Playlists tab
        pl_tab = QWidget()
        pl_layout = QVBoxLayout(pl_tab)

        # M3U URL
        url_group = QGroupBox("Add M3U Playlist")
        url_form = QFormLayout(url_group)
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://example.com/playlist.m3u")
        url_form.addRow("URL:", self._url_edit)
        add_url_btn = QPushButton("Add from URL")
        add_url_btn.setObjectName("primary")
        add_url_btn.clicked.connect(self._add_from_url)
        url_form.addRow(add_url_btn)

        add_file_btn = QPushButton("Add from File")
        add_file_btn.clicked.connect(self._add_from_file)
        url_form.addRow(add_file_btn)
        pl_layout.addWidget(url_group)

        # Playlists list
        pl_layout.addWidget(QLabel("Your Playlists"))
        self._playlist_list = QListWidget()
        self._playlist_list.itemClicked.connect(self._remove_playlist_prompt)
        pl_layout.addWidget(self._playlist_list)
        layout.addWidget(tabs)

        # Xtream tab
        xt_tab = QWidget()
        xt_layout = QVBoxLayout(xt_tab)

        xt_group = QGroupBox("Add Xtream Codes Provider")
        xt_form = QFormLayout(xt_group)
        self._xt_name = QLineEdit()
        xt_form.addRow("Name:", self._xt_name)
        self._xt_server = QLineEdit()
        self._xt_server.setPlaceholderText("http://example.com:8080")
        xt_form.addRow("Server:", self._xt_server)
        self._xt_user = QLineEdit()
        xt_form.addRow("Username:", self._xt_user)
        self._xt_pass = QLineEdit()
        self._xt_pass.setEchoMode(QLineEdit.Password)
        xt_form.addRow("Password:", self._xt_pass)
        add_xt_btn = QPushButton("Add Provider")
        add_xt_btn.setObjectName("primary")
        add_xt_btn.clicked.connect(self._add_xtream)
        xt_form.addRow(add_xt_btn)
        xt_layout.addWidget(xt_group)

        xt_layout.addWidget(QLabel("Your Providers"))
        self._provider_list = QListWidget()
        self._provider_list.itemClicked.connect(self._remove_provider_prompt)
        xt_layout.addWidget(self._provider_list)

        # Data tab
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        clear_fav = QPushButton("Clear Favorites")
        clear_fav.clicked.connect(self._clear_favorites)
        data_layout.addWidget(clear_fav)
        clear_recent = QPushButton("Clear Recently Viewed")
        clear_recent.clicked.connect(self._clear_recent)
        data_layout.addWidget(clear_recent)
        clear_positions = QPushButton("Clear Playback Positions")
        clear_positions.clicked.connect(self._clear_positions)
        data_layout.addWidget(clear_positions)
        data_layout.addStretch()

        tabs.addTab(pl_tab, "Playlists")
        tabs.addTab(xt_tab, "Xtream")
        tabs.addTab(data_tab, "Data")

    def _refresh_lists(self):
        self._playlist_list.clear()
        for pl in self._state.get_playlists():
            item = QListWidgetItem(f"{pl.name} ({len(pl.channels)} channels)")
            item.setData(Qt.UserRole, pl)
            self._playlist_list.addItem(item)

        self._provider_list.clear()
        for p in self._state.get_xtream_providers():
            name = p.get("name", "Unknown")
            server = p.get("server", "")
            item = QListWidgetItem(f"{name} ({server})")
            item.setData(Qt.UserRole, p)
            self._provider_list.addItem(item)

    def _add_from_url(self):
        url = self._url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a playlist URL")
            return
        asyncio.create_task(self._do_add_url(url))

    async def _do_add_url(self, url: str):
        try:
            playlist = await M3UParser.parse_from_url(url)
            self._state.add_playlist(playlist)
            self._url_edit.clear()
            self._refresh_lists()
            QMessageBox.information(self, "Success", f"Added {len(playlist.channels)} channels")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load playlist: {e}")

    def _add_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select M3U Playlist", "", "M3U Files (*.m3u *.m3u8);;All Files (*)")
        if path:
            asyncio.create_task(self._do_add_file(path))

    async def _do_add_file(self, path: str):
        try:
            playlist = await M3UParser.parse_from_file(path)
            self._state.add_playlist(playlist)
            self._refresh_lists()
            QMessageBox.information(self, "Success", f"Added {len(playlist.channels)} channels")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def _add_xtream(self):
        creds = XtreamCredentials(
            name=self._xt_name.text().strip() or "Xtream Provider",
            server=self._xt_server.text().strip(),
            username=self._xt_user.text().strip(),
            password=self._xt_pass.text().strip(),
        )
        if not all([creds.server, creds.username, creds.password]):
            QMessageBox.warning(self, "Missing Fields", "Please fill all Xtream fields")
            return
        asyncio.create_task(self._do_add_xtream(creds))

    async def _do_add_xtream(self, creds: XtreamCredentials):
        try:
            client = XtreamCodesClient(creds)
            info = await client.authenticate()
            channels = await client.get_all_channels()
            from ..models.playlist import Playlist
            pl = Playlist(
                name=creds.name,
                source=creds.server,
                channels=channels,
                metadata=creds.to_dict(),
            )
            self._state.add_playlist(pl)
            self._state.add_xtream_provider(creds)
            self._xt_name.clear()
            self._xt_server.clear()
            self._xt_user.clear()
            self._xt_pass.clear()
            self._refresh_lists()
            QMessageBox.information(self, "Success", f"Added {len(channels)} channels\nStatus: {info.status}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add provider: {e}")

    def _remove_playlist_prompt(self, item: QListWidgetItem):
        pl = item.data(Qt.UserRole)
        if pl and QMessageBox.question(self, "Remove Playlist", f"Remove {pl.name}?") == QMessageBox.Yes:
            self._state.remove_playlist(pl)
            self._refresh_lists()

    def _remove_provider_prompt(self, item: QListWidgetItem):
        p = item.data(Qt.UserRole)
        if p and QMessageBox.question(self, "Remove Provider", f"Remove {p.get('name')}?") == QMessageBox.Yes:
            self._state.remove_xtream_provider(p.get("server", ""), p.get("username", ""))
            self._refresh_lists()

    def _clear_favorites(self):
        self._state.clear_favorites()
        QMessageBox.information(self, "Done", "Favorites cleared")

    def _clear_recent(self):
        self._state.clear_recently_viewed()
        QMessageBox.information(self, "Done", "Recently viewed cleared")

    def _clear_positions(self):
        self._state.clear_playback_positions()
        QMessageBox.information(self, "Done", "Playback positions cleared")
