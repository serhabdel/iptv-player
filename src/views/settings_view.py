"""Settings view for managing playlists and preferences."""
import flet as ft
import asyncio
from typing import Optional, Callable
from ..services.state_manager import StateManager
from ..services.m3u_parser import M3UParser
from ..services.xtream_client import XtreamCodesClient, XtreamCredentials


class SettingsView(ft.Container):
    """Settings view for playlist management and preferences."""
    
    def __init__(
        self,
        state_manager: StateManager,
        on_back: Optional[Callable] = None,
    ):
        super().__init__()
        self._state = state_manager
        self._on_back = on_back
        self._is_loading = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the settings view."""
        # Header
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                tooltip="Back",
                                on_click=lambda e: self._on_back() if self._on_back else None,
                            ),
                            ft.Text(
                                "Settings",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.WHITE10)),
        )
        
        # URL input
        self._url_field = ft.TextField(
            label="M3U Playlist URL",
            hint_text="https://example.com/playlist.m3u",
            prefix_icon=ft.Icons.LINK_ROUNDED,
            border_radius=12,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.PURPLE_400,
            label_style=ft.TextStyle(color=ft.Colors.WHITE70),
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            expand=True,
        )
        
        self._add_button = ft.ElevatedButton(
            text="Add Playlist",
            icon=ft.Icons.ADD_ROUNDED,
            bgcolor=ft.Colors.PURPLE_700,
            color=ft.Colors.WHITE,
            on_click=self._add_playlist_from_url,
        )
        
        # Loading progress with real status
        self._progress_bar = ft.ProgressBar(
            width=400,
            color=ft.Colors.PURPLE_400,
            bgcolor=ft.Colors.WHITE10,
            value=None,  # Indeterminate initially
        )
        
        self._progress_text = ft.Text(
            "Connecting...",
            color=ft.Colors.WHITE70,
            size=13,
        )
        
        self._download_info = ft.Text(
            "",
            color=ft.Colors.WHITE54,
            size=11,
        )
        
        self._loading_container = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.ProgressRing(width=20, height=20, color=ft.Colors.PURPLE_400),
                            ft.Container(width=12),
                            self._progress_text,
                        ],
                    ),
                    ft.Container(height=8),
                    self._progress_bar,
                    ft.Container(height=4),
                    self._download_info,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            visible=False,
            padding=ft.padding.all(16),
        )
        
        self._status_text = ft.Text(
            "",
            color=ft.Colors.WHITE70,
            size=12,
        )
        
        # File picker
        self._file_picker = ft.FilePicker(
            on_result=self._on_file_picked,
        )
        
        # Playlist list
        self._playlist_list = ft.ListView(
            spacing=8,
            padding=ft.padding.symmetric(vertical=8),
        )
        self._update_playlist_list()
        
        add_url_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Add Playlist from URL",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Container(height=12),
                    ft.Row(
                        [
                            self._url_field,
                            self._add_button,
                        ],
                        spacing=12,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    self._loading_container,
                    self._status_text,
                ],
            ),
            padding=ft.padding.all(20),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
        )
        
        add_file_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Add Playlist from File",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                "(Recommended for large playlists)",
                                size=12,
                                color=ft.Colors.GREEN_300,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=12),
                    ft.OutlinedButton(
                        text="Browse for M3U file...",
                        icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE70,
                            side=ft.BorderSide(1, ft.Colors.WHITE24),
                        ),
                        on_click=lambda e: self._file_picker.pick_files(
                            allowed_extensions=["m3u", "m3u8"],
                            dialog_title="Select M3U Playlist",
                        ),
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "💡 Tip: For 8K+ channel playlists, download the file first using your browser or wget, then add it here.",
                        size=11,
                        color=ft.Colors.WHITE38,
                    ),
                ],
            ),
            padding=ft.padding.all(20),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
        )
        
        playlists_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "My Playlists",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    str(len(self._state.get_playlists())),
                                    size=12,
                                    color=ft.Colors.WHITE,
                                ),
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                border_radius=12,
                                bgcolor=ft.Colors.PURPLE_700,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Container(height=4),
                    ft.Text(
                        "★ = Default playlist (loads on startup)",
                        size=11,
                        color=ft.Colors.WHITE38,
                    ),
                    ft.Container(height=12),
                    self._playlist_list,
                ],
                expand=True,
            ),
            padding=ft.padding.all(20),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            expand=True,
        )
        
        # Xtream Codes section
        self._xtream_server_field = ft.TextField(
            label="Server URL",
            hint_text="http://example.com:8080",
            prefix_icon=ft.Icons.DNS_ROUNDED,
            border_radius=12,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
            label_style=ft.TextStyle(color=ft.Colors.WHITE70),
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            expand=True,
        )
        
        self._xtream_username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON_ROUNDED,
            border_radius=12,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
            label_style=ft.TextStyle(color=ft.Colors.WHITE70),
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            expand=True,
        )
        
        self._xtream_password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.Icons.LOCK_ROUNDED,
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
            label_style=ft.TextStyle(color=ft.Colors.WHITE70),
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            expand=True,
        )
        
        self._xtream_status_text = ft.Text(
            "",
            color=ft.Colors.WHITE70,
            size=12,
        )
        
        self._xtream_provider_list = ft.ListView(
            spacing=8,
            padding=ft.padding.symmetric(vertical=8),
            height=150,
        )
        self._update_xtream_provider_list()
        
        xtream_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.LIVE_TV_ROUNDED, color=ft.Colors.BLUE_400, size=24),
                            ft.Text(
                                "Xtream Codes Provider",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=12),
                    self._xtream_server_field,
                    ft.Row(
                        [
                            self._xtream_username_field,
                            self._xtream_password_field,
                        ],
                        spacing=12,
                    ),
                    ft.Container(height=8),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                text="Test Connection",
                                icon=ft.Icons.WIFI_TETHERING_ROUNDED,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE70,
                                    side=ft.BorderSide(1, ft.Colors.WHITE24),
                                ),
                                on_click=self._test_xtream_connection,
                            ),
                            ft.ElevatedButton(
                                text="Add Provider",
                                icon=ft.Icons.ADD_ROUNDED,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                on_click=self._add_xtream_provider,
                            ),
                        ],
                        spacing=12,
                    ),
                    self._xtream_status_text,
                    ft.Container(height=8),
                    ft.Text(
                        "Saved Providers:",
                        size=12,
                        color=ft.Colors.WHITE54,
                    ),
                    self._xtream_provider_list,
                ],
            ),
            padding=ft.padding.all(20),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
        )
        
        self.content = ft.Column(
            [
                header,
                ft.Container(
                    content=ft.Column(
                        [
                            add_url_section,
                            add_file_section,
                            xtream_section,
                            playlists_section,
                        ],
                        spacing=16,
                        expand=True,
                    ),
                    padding=ft.padding.all(20),
                    expand=True,
                ),
                self._file_picker,
            ],
            expand=True,
            spacing=0,
        )
        self.expand = True
        self.bgcolor = "#0a0a0f"
    
    def _update_progress(self, downloaded: int, total: int):
        """Update progress callback - called from parser."""
        if total > 0:
            percent = downloaded / total
            self._progress_bar.value = percent
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._progress_text.value = f"Downloading... {int(percent * 100)}%"
            self._download_info.value = f"{mb_downloaded:.1f} MB / {mb_total:.1f} MB"
            if self.page:
                self.page.update()
    
    def _update_playlist_list(self):
        """Update the playlist list display."""
        self._playlist_list.controls.clear()
        
        playlists = self._state.get_playlists()
        default_source = self._state.get_setting("default_playlist", None)
        
        if not playlists:
            self._playlist_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.PLAYLIST_ADD_ROUNDED,
                                size=48,
                                color=ft.Colors.WHITE30,
                            ),
                            ft.Text(
                                "No playlists added yet",
                                color=ft.Colors.WHITE30,
                                size=14,
                            ),
                            ft.Text(
                                "Add a playlist URL or file above",
                                color=ft.Colors.WHITE24,
                                size=12,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(32),
                )
            )
        else:
            for playlist in playlists:
                is_default = playlist.source == default_source
                self._playlist_list.controls.append(
                    self._build_playlist_tile(playlist, is_default)
                )
    
    def _build_playlist_tile(self, playlist, is_default: bool) -> ft.Control:
        """Build a playlist list tile."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.PLAYLIST_PLAY_ROUNDED,
                        color=ft.Colors.YELLOW_400 if is_default else ft.Colors.PURPLE_400,
                        size=32,
                    ),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        playlist.name,
                                        size=14,
                                        weight=ft.FontWeight.W_500,
                                        color=ft.Colors.WHITE,
                                    ),
                                    ft.Text(
                                        "★ DEFAULT" if is_default else "",
                                        size=10,
                                        color=ft.Colors.YELLOW_400,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.Text(
                                f"{len(playlist.channels)} channels",
                                size=12,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.STAR_ROUNDED if is_default else ft.Icons.STAR_BORDER_ROUNDED,
                        icon_color=ft.Colors.YELLOW_400 if is_default else ft.Colors.WHITE38,
                        tooltip="Set as default",
                        on_click=lambda e, p=playlist: self._set_default(p),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_color=ft.Colors.RED_300,
                        tooltip="Remove playlist",
                        on_click=lambda e, p=playlist: self._remove_playlist(p),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.YELLOW_700) if is_default else None,
        )
    
    def _set_default(self, playlist):
        """Set a playlist as default."""
        self._state.set_setting("default_playlist", playlist.source)
        self._update_playlist_list()
        if self.page:
            self.page.update()
    
    async def _add_playlist_from_url(self, e):
        """Add playlist from URL with real progress tracking."""
        url = self._url_field.value.strip()
        
        if not url:
            self._status_text.value = "Please enter a URL"
            self._status_text.color = ft.Colors.RED_300
            if self.page:
                self.page.update()
            return
        
        self._is_loading = True
        self._loading_container.visible = True
        self._add_button.disabled = True
        self._status_text.value = ""
        self._progress_bar.value = None  # Indeterminate while connecting
        self._progress_text.value = "Connecting..."
        self._download_info.value = ""
        if self.page:
            self.page.update()
        
        try:
            # Parse playlist with progress callback
            playlist = await M3UParser.parse_from_url(
                url,
                progress_callback=self._update_progress
            )
            
            # Parsing phase
            self._progress_text.value = "Parsing channels..."
            self._progress_bar.value = None
            if self.page:
                self.page.update()
            
            await asyncio.sleep(0.5)  # Brief pause for UI
            
            self._state.add_playlist(playlist)
            
            self._url_field.value = ""
            self._status_text.value = f"✓ Added {len(playlist.channels)} channels from {playlist.name}"
            self._status_text.color = ft.Colors.GREEN_300
            self._update_playlist_list()
            
            # Set as default if first
            if len(self._state.get_playlists()) == 1:
                self._state.set_setting("default_playlist", playlist.source)
                self._update_playlist_list()
                
        except Exception as ex:
            self._status_text.value = f"Error: {str(ex)}"
            self._status_text.color = ft.Colors.RED_300
        finally:
            self._is_loading = False
            self._loading_container.visible = False
            self._add_button.disabled = False
            if self.page:
                self.page.update()
    
    async def _on_file_picked(self, e: ft.FilePickerResultEvent):
        """Handle file picker result."""
        if not e.files:
            return
        
        file = e.files[0]
        
        self._loading_container.visible = True
        self._progress_bar.value = None
        self._progress_text.value = "Loading file..."
        self._download_info.value = ""
        if self.page:
            self.page.update()
        
        try:
            playlist = await M3UParser.parse_from_file(file.path)
            
            self._state.add_playlist(playlist)
            
            self._status_text.value = f"✓ Added {len(playlist.channels)} channels from {playlist.name}"
            self._status_text.color = ft.Colors.GREEN_300
            self._update_playlist_list()
            
            # Set as default if first
            if len(self._state.get_playlists()) == 1:
                self._state.set_setting("default_playlist", playlist.source)
                self._update_playlist_list()
                
        except Exception as ex:
            self._status_text.value = f"Error: {str(ex)}"
            self._status_text.color = ft.Colors.RED_300
        finally:
            self._loading_container.visible = False
            if self.page:
                self.page.update()
    
    def _remove_playlist(self, playlist):
        """Remove a playlist."""
        # If removing default, clear the setting
        if self._state.get_setting("default_playlist") == playlist.source:
            self._state.set_setting("default_playlist", None)
        
        self._state.remove_playlist(playlist)
        self._update_playlist_list()
        if self.page:
            self.page.update()
    
    # Xtream Codes Methods
    def _update_xtream_provider_list(self):
        """Update the Xtream Codes provider list display."""
        self._xtream_provider_list.controls.clear()
        
        providers = self._state.get_xtream_providers()
        
        if not providers:
            self._xtream_provider_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No Xtream providers added yet",
                        color=ft.Colors.WHITE30,
                        size=12,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(16),
                )
            )
        else:
            for provider in providers:
                self._xtream_provider_list.controls.append(
                    self._build_xtream_provider_tile(provider)
                )
    
    def _build_xtream_provider_tile(self, provider: dict) -> ft.Control:
        """Build a provider list tile."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIVE_TV_ROUNDED,
                        color=ft.Colors.BLUE_400,
                        size=24,
                    ),
                    ft.Container(width=8),
                    ft.Column(
                        [
                            ft.Text(
                                provider.get("name", "Xtream Provider"),
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                f"{provider.get('server', '')} • {provider.get('username', '')}",
                                size=11,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_color=ft.Colors.BLUE_300,
                        tooltip="Refresh channels",
                        on_click=lambda e, p=provider: self.page.run_task(
                            self._refresh_xtream_channels, p
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_color=ft.Colors.RED_300,
                        tooltip="Remove provider",
                        on_click=lambda e, p=provider: self._remove_xtream_provider(p),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        )
    
    async def _test_xtream_connection(self, e):
        """Test Xtream Codes connection."""
        server = self._xtream_server_field.value.strip()
        username = self._xtream_username_field.value.strip()
        password = self._xtream_password_field.value.strip()
        
        if not server or not username or not password:
            self._xtream_status_text.value = "Please fill in all fields"
            self._xtream_status_text.color = ft.Colors.RED_300
            if self.page:
                self.page.update()
            return
        
        self._xtream_status_text.value = "Testing connection..."
        self._xtream_status_text.color = ft.Colors.WHITE70
        if self.page:
            self.page.update()
        
        try:
            credentials = XtreamCredentials(
                name=f"Test ({username})",
                server=server,
                username=username,
                password=password,
            )
            client = XtreamCodesClient(credentials)
            account_info = await client.authenticate()
            
            self._xtream_status_text.value = (
                f"✓ Connected! Status: {account_info.status}, "
                f"Max connections: {account_info.max_connections}"
            )
            self._xtream_status_text.color = ft.Colors.GREEN_300
            
        except Exception as ex:
            self._xtream_status_text.value = f"Connection failed: {str(ex)}"
            self._xtream_status_text.color = ft.Colors.RED_300
        
        if self.page:
            self.page.update()
    
    async def _add_xtream_provider(self, e):
        """Add Xtream Codes provider and load channels."""
        server = self._xtream_server_field.value.strip()
        username = self._xtream_username_field.value.strip()
        password = self._xtream_password_field.value.strip()
        
        if not server or not username or not password:
            self._xtream_status_text.value = "Please fill in all fields"
            self._xtream_status_text.color = ft.Colors.RED_300
            if self.page:
                self.page.update()
            return
        
        self._xtream_status_text.value = "Adding provider and loading channels..."
        self._xtream_status_text.color = ft.Colors.WHITE70
        if self.page:
            self.page.update()
        
        try:
            credentials = XtreamCredentials(
                name=f"Xtream ({username})",
                server=server,
                username=username,
                password=password,
            )
            client = XtreamCodesClient(credentials)
            
            # Test connection first
            account_info = await client.authenticate()
            
            # Save credentials
            self._state.add_xtream_provider(credentials)
            
            # Load live channels
            channels = await client.get_live_streams()
            
            # Create a playlist from the channels
            from ..models.playlist import Playlist
            playlist = Playlist(
                name=f"Xtream: {username}",
                source=f"xtream://{server}",
                channels=channels,
            )
            self._state.add_playlist(playlist)
            
            # Clear fields
            self._xtream_server_field.value = ""
            self._xtream_username_field.value = ""
            self._xtream_password_field.value = ""
            
            self._xtream_status_text.value = f"✓ Added {len(channels)} channels from {username}"
            self._xtream_status_text.color = ft.Colors.GREEN_300
            
            self._update_xtream_provider_list()
            self._update_playlist_list()
            
        except Exception as ex:
            self._xtream_status_text.value = f"Error: {str(ex)}"
            self._xtream_status_text.color = ft.Colors.RED_300
        
        if self.page:
            self.page.update()
    
    async def _refresh_xtream_channels(self, provider: dict):
        """Refresh channels from an Xtream provider."""
        try:
            credentials = XtreamCredentials.from_dict(provider)
            client = XtreamCodesClient(credentials)
            
            channels = await client.get_live_streams()
            
            # Find and update the playlist
            from ..models.playlist import Playlist
            playlist = Playlist(
                name=f"Xtream: {credentials.username}",
                source=f"xtream://{credentials.server}",
                channels=channels,
            )
            
            # Remove old playlist with same source
            for p in self._state.get_playlists():
                if p.source == playlist.source:
                    self._state.remove_playlist(p)
                    break
            
            self._state.add_playlist(playlist)
            self._update_playlist_list()
            
            if self.page:
                self.page.update()
                
        except Exception:
            pass  # Silent fail for refresh
    
    def _remove_xtream_provider(self, provider: dict):
        """Remove an Xtream provider."""
        server = provider.get("server", "")
        username = provider.get("username", "")
        
        self._state.remove_xtream_provider(server, username)
        
        # Also remove associated playlist
        source = f"xtream://{server}"
        for p in self._state.get_playlists():
            if p.source == source:
                self._state.remove_playlist(p)
                break
        
        self._update_xtream_provider_list()
        self._update_playlist_list()
        
        if self.page:
            self.page.update()
