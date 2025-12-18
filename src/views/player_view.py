"""Main player view with video player and channel sidebar."""
import flet as ft
from typing import Optional, Callable, List
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
            on_next=self._on_next_channel,
            on_prev=self._on_prev_channel,
            get_next_channel=self._get_next_channel_obj,
        )
        
        # Cast overlay container (initially hidden)
        self._cast_overlay = ft.Container(
            visible=False,
            expand=True,
            alignment=ft.alignment.center,
        )
        # Pass overlay to video player
        self._video_player.set_overlay_container(self._cast_overlay)
        
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
        
        # Playlist Selector
        self._playlist_selector = ft.Dropdown(
            width=200,
            text_size=14,
            color=ft.Colors.WHITE,
            bgcolor="#1a1a2e",
            border_color=ft.Colors.WHITE10,
            border_radius=8,
            options=self._get_playlist_options(),
            value="All Playlists",
            on_change=self._on_playlist_filter_change,
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
                            self._playlist_selector,
                            self._sidebar_toggle,
                            settings_btn,
                        ],
                        spacing=8,
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
        
        # Video container
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
        
        self.content = ft.Stack(
            [
                ft.Column(
                    [
                        header,
                        main_content,
                    ],
                    expand=True,
                    spacing=0,
                ),
                self._cast_overlay,
            ],
            expand=True,
        )
        self.expand = True
        self.bgcolor = "#0a0a12"
        
        # Subscribe to state changes
        self._state.on_playlist_change(self._on_playlist_change)
        self._state.on_favorites_change(self._on_favorites_change)
    
    def refresh(self):
        """Refresh the view with current state."""
        # Update filter options
        self._playlist_selector.options = self._get_playlist_options()
        if self._playlist_selector.page:
            self._playlist_selector.update()
        
        # Refresh channels with current filter
        filter_val = self._playlist_selector.value
        self._channel_list.set_channels(
            self._state.get_all_channels(playlist_filter=filter_val),
            self._state.get_all_groups(playlist_filter=filter_val),
        )
    
    def _get_playlist_options(self) -> List[ft.dropdown.Option]:
        """Get options for playlist selector."""
        options = [ft.dropdown.Option("All Playlists")]
        playlists = self._state.get_playlists()
        for p in playlists:
            options.append(ft.dropdown.Option(p.name))
        return options
    
    def _on_playlist_filter_change(self, e):
        """Handle playlist filter change."""
        filter_val = self._playlist_selector.value
        self._channel_list.set_channels(
            self._state.get_all_channels(playlist_filter=filter_val),
            self._state.get_all_groups(playlist_filter=filter_val),
        )
        self._channel_list.refresh()

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
        self._channel_list.refresh()

    def _on_next_channel(self):
        """Navigate to next channel."""
        self._navigate_channel(1)

    def _on_prev_channel(self):
        """Navigate to previous channel."""
        self._navigate_channel(-1)

    def _navigate_channel(self, delta: int):
        """Navigate channels by delta."""
        current = self._state.current_channel
        if not current:
            return
            
        # Get current list based on filter
        filter_val = self._playlist_selector.value
        media_list = self._state.get_all_channels(playlist_filter=filter_val)
        
        if not media_list:
            return
            
        try:
            # Find current index
            # Note: This might be slow for large lists, optimization potential
            idx = -1
            for i, ch in enumerate(media_list):
                if ch.url == current.url:  # Compare by URL as likely unique ID
                    idx = i
                    break
            
            if idx != -1:
                new_idx = (idx + delta) % len(media_list)
                new_channel = media_list[new_idx]
                self._on_channel_select(new_channel)
        except Exception:
            pass

    def _get_next_channel_obj(self) -> Optional[Channel]:
        """Get the next channel object without navigating."""
        current = self._state.get_current_channel()
        if not current: return None
        
        filter_val = self._playlist_selector.value
        media_list = self._state.get_all_channels(playlist_filter=filter_val)
        if not media_list: return None
        
        for i, ch in enumerate(media_list):
            if ch.url == current.url:
                new_idx = (i + 1) % len(media_list)
                return media_list[new_idx]
        return None
