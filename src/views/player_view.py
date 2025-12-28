"""Player view - Full screen video player for hub-based navigation."""
import flet as ft
from typing import Optional, Callable, List
from ..components.video_player import VideoPlayerComponent
from ..models.channel import Channel
from ..services.state_manager import StateManager


class PlayerView(ft.Container):
    """Full screen video player view (hub navigation version)."""
    
    def __init__(
        self,
        state_manager: StateManager,
        on_back: Optional[Callable] = None,
        on_settings_click: Optional[Callable] = None,
    ):
        super().__init__()
        self._state = state_manager
        self._on_back = on_back
        self._on_settings_click = on_settings_click
        
        # Episode context for series navigation
        self._episode_list: List[Channel] = []
        
        # Create video player once (don't recreate on refresh)
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
        
        # Channel info text (will be updated)
        self._channel_name_text = ft.Text(
            "Select a channel",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._channel_group_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.WHITE54,
        )
        
        # Favorite button
        self._favorite_button = ft.IconButton(
            icon=ft.Icons.FAVORITE_BORDER_ROUNDED,
            icon_color=ft.Colors.WHITE38,
            icon_size=24,
            tooltip="Add to favorites",
            on_click=self._toggle_favorite,
        )
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the player view."""
        # Header with back button
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                icon_size=24,
                                tooltip="Back to channels",
                                on_click=self._handle_back_click,
                            ),
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.LIVE_TV_ROUNDED,
                                    color=ft.Colors.WHITE,
                                    size=20,
                                ),
                                width=36,
                                height=36,
                                border_radius=10,
                                gradient=ft.LinearGradient(
                                    colors=[ft.Colors.PURPLE_700, ft.Colors.PURPLE_400],
                                    begin=ft.alignment.top_left,
                                    end=ft.alignment.bottom_right,
                                ),
                                alignment=ft.alignment.center,
                            ),
                            ft.Column(
                                [
                                    self._channel_name_text,
                                    self._channel_group_text,
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        [
                            # Favorite toggle
                            self._favorite_button,
                            # Previous channel
                            ft.IconButton(
                                icon=ft.Icons.SKIP_PREVIOUS_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                tooltip="Previous channel",
                                on_click=lambda e: self._on_prev_channel(),
                            ),
                            # Next channel
                            ft.IconButton(
                                icon=ft.Icons.SKIP_NEXT_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                tooltip="Next channel",
                                on_click=lambda e: self._on_next_channel(),
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor="#1a1a2e",
        )
        
        # Video container (full area - no padding)
        video_container = ft.Container(
            content=self._video_player,
            expand=True,
            bgcolor="#0a0a12",
        )
        
        self.content = ft.Stack(
            [
                ft.Column(
                    [
                        header,
                        video_container,
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
    
    def refresh(self):
        """Refresh the header with current channel info."""
        current = self._state.get_current_channel()
        if current:
            self._channel_name_text.value = current.name
            self._channel_group_text.value = current.group
        if self.page:
            self.update()
    
    def _handle_back_click(self, e):
        """Handle back button click."""
        # Stop playback
        self._video_player.stop()
        
        # Navigate back
        if self._on_back:
            self._on_back()

    def set_episode_context(self, episodes: List[Channel]):
        """Set the episode list for series navigation.
        
        When playing from a series, this should be called with the episode list
        so that next/prev buttons navigate within the series.
        Call with empty list to clear the context.
        """
        self._episode_list = episodes
    
    def play_channel(self, channel: Channel):
        """Start playing a channel."""
        self._state.set_current_channel(channel)
        self._state.add_to_recently_viewed(channel)
        
        # Update header info
        self._channel_name_text.value = channel.name
        self._channel_group_text.value = channel.group
        
        # Update favorite button state
        self._update_favorite_button(channel)
        
        # Play the channel
        self._video_player.play_channel(channel)
    
    def _on_video_error(self, error: str):
        """Handle video playback error."""
        if self.page:
             self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Playback Error: {error}"))
             self.page.snack_bar.open = True
             self.page.update()
    
    def _toggle_favorite(self, e):
        """Toggle favorite status of current channel."""
        current = self._state.get_current_channel()
        if current:
            is_fav = self._state.toggle_favorite(current)
            self._update_favorite_button(current)
            if self.page:
                self._favorite_button.update()
    
    def _update_favorite_button(self, channel: Channel):
        """Update favorite button appearance based on channel state."""
        is_fav = self._state.is_favorite(channel)
        self._favorite_button.icon = ft.Icons.FAVORITE_ROUNDED if is_fav else ft.Icons.FAVORITE_BORDER_ROUNDED
        self._favorite_button.icon_color = ft.Colors.PINK_400 if is_fav else ft.Colors.WHITE38
        self._favorite_button.tooltip = "Remove from favorites" if is_fav else "Add to favorites"
    
    def _on_next_channel(self):
        """Navigate to next channel."""
        self._navigate_channel(1)
    
    def _on_prev_channel(self):
        """Navigate to previous channel."""
        self._navigate_channel(-1)
    
    def _navigate_channel(self, delta: int):
        """Navigate channels by delta."""
        current = self._state.get_current_channel()
        if not current:
            return
        
        # Get all channels
        # Use episode list if available (for series), otherwise use all channels
        if self._episode_list:
            media_list = self._episode_list
        else:
            media_list = self._state.get_all_channels()
        
        if not media_list:
            return
        
        try:
            # Find current index
            idx = -1
            for i, ch in enumerate(media_list):
                if ch.url == current.url:
                    idx = i
                    break
            
            if idx != -1:
                new_idx = (idx + delta) % len(media_list)
                new_channel = media_list[new_idx]
                self.play_channel(new_channel)
        except Exception:
            pass
    
    def _get_next_channel_obj(self) -> Optional[Channel]:
        """Get the next channel object without navigating."""
        current = self._state.get_current_channel()
        if not current:
            return None
        
        # Use episode list if available (for series), otherwise use all channels
        if self._episode_list:
            media_list = self._episode_list
        else:
            media_list = self._state.get_all_channels()
        if not media_list:
            return None
        
        for i, ch in enumerate(media_list):
            if ch.url == current.url:
                new_idx = (i + 1) % len(media_list)
                return media_list[new_idx]
        return None
