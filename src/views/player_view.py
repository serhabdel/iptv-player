"""Main player view with video player and channel sidebar."""
import flet as ft
from typing import Optional, Callable
from ..components.video_player import VideoPlayerComponent
from ..components.channel_list import ChannelList
from ..models.channel import Channel
from ..services.state_manager import StateManager


class PlayerView(ft.Container):
    """Main player view with video and channel list."""
    
    def __init__(
        self,
        state_manager: StateManager,
        on_settings_click: Optional[Callable] = None,
    ):
        super().__init__()
        self._state = state_manager
        self._on_settings_click = on_settings_click
        self._is_sidebar_collapsed = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the player view."""
        self._video_player = VideoPlayerComponent(
            on_error=self._on_video_error,
        )
        
        self._channel_list = ChannelList(
            channels=self._state.get_all_channels(),
            groups=self._state.get_all_groups(),
            on_channel_select=self._on_channel_select,
            on_favorite_toggle=self._on_favorite_toggle,
        )
        
        # Sidebar toggle button
        self._sidebar_toggle = ft.IconButton(
            icon=ft.Icons.MENU_OPEN_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            tooltip="Toggle sidebar",
            on_click=self._toggle_sidebar,
        )
        
        # Settings button
        settings_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            tooltip="Settings",
            on_click=lambda e: self._on_settings_click() if self._on_settings_click else None,
        )
        
        # Header with gradient
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.LIVE_TV_ROUNDED,
                                    color=ft.Colors.WHITE,
                                    size=24,
                                ),
                                width=44,
                                height=44,
                                border_radius=12,
                                gradient=ft.LinearGradient(
                                    colors=[ft.Colors.PURPLE_700, ft.Colors.PURPLE_400],
                                    begin=ft.alignment.top_left,
                                    end=ft.alignment.bottom_right,
                                ),
                                alignment=ft.alignment.center,
                            ),
                            ft.Text(
                                "IPTV Player",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=14,
                    ),
                    ft.Row(
                        [
                            self._sidebar_toggle,
                            settings_btn,
                        ],
                        spacing=4,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=16),
            gradient=ft.LinearGradient(
                colors=["#1a1a2e", "#16213e"],
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
            ),
        )
        
        # Sidebar with improved styling
        self._sidebar = ft.Container(
            content=self._channel_list,
            width=380,
            bgcolor="#0f0f1a",
            border=ft.border.only(left=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE))),
        )
        
        # Video container with padding
        video_container = ft.Container(
            content=self._video_player,
            expand=True,
            padding=ft.padding.all(20),
            bgcolor="#0a0a12",
        )
        
        # Main content area
        main_content = ft.Row(
            [
                video_container,
                self._sidebar,
            ],
            expand=True,
            spacing=0,
        )
        
        # Subscribe to state changes
        self._state.on_playlist_change(self._on_playlist_change)
        self._state.on_favorites_change(self._on_favorites_change)
        
        self.content = ft.Column(
            [
                header,
                main_content,
            ],
            expand=True,
            spacing=0,
        )
        self.expand = True
        self.bgcolor = "#0a0a12"
    
    def refresh(self):
        """Refresh the view with current state."""
        self._channel_list.set_channels(
            self._state.get_all_channels(),
            self._state.get_all_groups(),
        )
    
    def _on_channel_select(self, channel: Channel):
        """Handle channel selection."""
        self._state.set_current_channel(channel)
        self._video_player.play_channel(channel)
    
    def _on_favorite_toggle(self, channel: Channel):
        """Handle favorite toggle."""
        self._state.toggle_favorite(channel)
        self._channel_list.refresh()
    
    def _on_video_error(self, error: str):
        """Handle video playback error."""
        pass
    
    def _toggle_sidebar(self, e):
        """Toggle sidebar visibility."""
        self._is_sidebar_collapsed = not self._is_sidebar_collapsed
        
        if self._is_sidebar_collapsed:
            self._sidebar.visible = False
            self._sidebar_toggle.icon = ft.Icons.MENU_ROUNDED
        else:
            self._sidebar.visible = True
            self._sidebar_toggle.icon = ft.Icons.MENU_OPEN_ROUNDED
        
        if self.page:
            self.page.update()
    
    def _on_playlist_change(self):
        """Handle playlist changes."""
        self.refresh()
    
    def _on_favorites_change(self):
        """Handle favorites changes."""
        self._channel_list.refresh()
