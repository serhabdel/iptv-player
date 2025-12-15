"""Video player component for IPTV streams."""
import flet as ft
import flet_video as fv
import subprocess
from typing import Optional, Callable
from ..models.channel import Channel


class VideoPlayerComponent(ft.Column):
    """Custom video player component - simplified for better rendering."""
    
    def __init__(
        self,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self._on_error = on_error
        self._current_channel: Optional[Channel] = None
        self._is_playing = False
        self._video: Optional[fv.Video] = None
        self._current_volume = 100
        self._system_boost = 100  # Track system boost level
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the video player UI."""
        # Create video player with optimized settings for stability
        self._video = fv.Video(
            expand=True,
            fill_color="#000000",
            aspect_ratio=16/9,
            volume=100,
            autoplay=True,
            filter_quality=ft.FilterQuality.HIGH,
            show_controls=True,
            fit=ft.ImageFit.CONTAIN,
            on_loaded=self._on_video_loaded,
            on_error=self._on_video_error,
        )
        
        self._channel_info = ft.Text(
            "",
            color=ft.Colors.WHITE,
            size=14,
            weight=ft.FontWeight.W_600,
        )
        
        # Volume control (0-100 for app)
        self._volume_slider = ft.Slider(
            min=0,
            max=100,
            value=100,
            width=100,
            active_color=ft.Colors.PURPLE_400,
            thumb_color=ft.Colors.PURPLE_200,
            on_change=self._on_volume_change,
        )
        
        self._volume_text = ft.Text(
            "100%",
            size=12,
            color=ft.Colors.WHITE70,
            width=40,
        )
        
        self._volume_icon = ft.Icon(
            ft.Icons.VOLUME_UP_ROUNDED,
            color=ft.Colors.WHITE70,
            size=20,
        )
        
        # VLC-style boost slider (100% - 200%)
        self._boost_slider = ft.Slider(
            min=100,
            max=200,
            value=100,
            width=80,
            active_color=ft.Colors.ORANGE_400,
            thumb_color=ft.Colors.ORANGE_300,
            on_change=self._on_boost_change,
        )
        
        self._boost_text = ft.Text(
            "🔊",
            size=12,
            color=ft.Colors.WHITE54,
            tooltip="System audio boost (100-200%)",
        )
        
        # Fullscreen button
        self._fullscreen_btn = ft.IconButton(
            icon=ft.Icons.FULLSCREEN_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            icon_size=24,
            tooltip="Fullscreen (better quality)",
            on_click=self._toggle_fullscreen,
        )
        
        # Now playing bar with volume controls
        self._now_playing_bar = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIVE_TV_ROUNDED,
                        color=ft.Colors.PURPLE_400,
                        size=20,
                    ),
                    ft.Container(width=8),
                    self._channel_info,
                    ft.Container(expand=True),
                    # App Volume
                    self._volume_icon,
                    self._volume_slider,
                    self._volume_text,
                    ft.Container(width=8),
                    # System Boost
                    ft.Container(
                        content=ft.Row([
                            self._boost_text,
                            self._boost_slider,
                        ], spacing=4),
                        bgcolor="#2d1f3d",
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        tooltip="VLC-style boost (up to 200%)",
                    ),
                    ft.Container(width=8),
                    self._fullscreen_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor="#1a1a2e",
            border_radius=10,
            visible=False,
        )
        
        # Welcome message
        self._welcome = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED,
                        size=80,
                        color=ft.Colors.WHITE24,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "Select a channel to start watching",
                        color=ft.Colors.WHITE54,
                        size=16,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor="#0a0a12",
            border_radius=16,
        )
        
        # Video container with fixed background
        self._video_container = ft.Container(
            content=self._video,
            expand=True,
            border_radius=16,
            bgcolor="#000000",
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            visible=False,
        )
        
        # Build layout
        self.controls = [
            self._now_playing_bar,
            ft.Container(height=8),
            self._welcome,
            self._video_container,
        ]
        self.expand = True
        self.spacing = 0
    
    def _on_volume_change(self, e):
        """Handle app volume change."""
        volume = int(e.control.value)
        self._current_volume = volume
        self._video.volume = volume
        
        self._volume_text.value = f"{volume}%"
        
        if volume == 0:
            self._volume_icon.name = ft.Icons.VOLUME_OFF_ROUNDED
        elif volume < 50:
            self._volume_icon.name = ft.Icons.VOLUME_DOWN_ROUNDED
        else:
            self._volume_icon.name = ft.Icons.VOLUME_UP_ROUNDED
        
        if self.page:
            self.page.update()
    
    def _on_boost_change(self, e):
        """Handle system boost change (VLC-style 100-200%)."""
        boost = int(e.control.value)
        self._system_boost = boost
        
        # Update visual
        if boost > 100:
            self._boost_text.value = f"🔊 {boost}%"
            self._boost_text.color = ft.Colors.ORANGE_400
        else:
            self._boost_text.value = "🔊"
            self._boost_text.color = ft.Colors.WHITE54
        
        # Apply system boost using wpctl
        try:
            volume_factor = boost / 100.0
            subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", str(volume_factor)],
                capture_output=True,
                timeout=2
            )
        except Exception:
            # wpctl not available, try pactl
            try:
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{boost}%"],
                    capture_output=True,
                    timeout=2
                )
            except Exception:
                pass
        
        if self.page:
            self.page.update()
    
    def _toggle_fullscreen(self, e):
        """Toggle fullscreen mode."""
        if self.page:
            self.page.window.full_screen = not self.page.window.full_screen
            self.page.update()
    
    def play_channel(self, channel: Channel):
        """Start playing a channel."""
        self._current_channel = channel
        
        # Show video, hide welcome
        self._welcome.visible = False
        self._video_container.visible = True
        self._now_playing_bar.visible = True
        self._channel_info.value = channel.name
        
        try:
            # Add the new channel to playlist
            self._video.playlist_add(fv.VideoMedia(resource=channel.url))
            
            # Jump to the new item
            playlist_len = len(self._video.playlist)
            if playlist_len > 0:
                self._video.jump_to(playlist_len - 1)
            
            self._video.play()
            self._is_playing = True
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
        
        if self.page:
            self.page.update()
    
    def _on_video_loaded(self, e):
        """Handle video loaded event."""
        if self.page:
            self.page.update()
    
    def _on_video_error(self, e):
        """Handle video error event."""
        if self._on_error:
            self._on_error("Failed to load stream")
