"""Video player component for IPTV streams."""
import flet as ft
import flet_video as fv
import subprocess
import asyncio
from typing import Optional, Callable, List
from ..models.channel import Channel
from ..services.dlna_client import DLNACastService, DLNADevice
from ..services.stream_proxy import get_stream_proxy
from .track_selector import TrackSelector


class VideoPlayerComponent(ft.Column):
    """Custom video player component - simplified for better rendering."""
    
    def __init__(
        self,
        on_error: Optional[Callable[[str], None]] = None,
        on_next: Optional[Callable[[], None]] = None,
        on_prev: Optional[Callable[[], None]] = None,
        get_next_channel: Optional[Callable[[], Optional[Channel]]] = None,
    ):
        super().__init__()
        self._on_error = on_error
        self._on_next = on_next
        self._on_prev = on_prev
        self._get_next_channel = get_next_channel
        self._current_channel: Optional[Channel] = None
        self._is_playing = False
        self._video: Optional[fv.Video] = None
        self._current_volume = 100
        self._system_boost = 100  # Track system boost level
        self._dlna_service = DLNACastService()
        self._discovered_devices: List[DLNADevice] = []
        self._stream_proxy = get_stream_proxy()
        self._overlay_container: Optional[ft.Container] = None
        
        # Track selection state
        self._audio_tracks: List[dict] = []
        self._subtitle_tracks: List[dict] = []
        self._current_audio_track: int = 0
        self._current_subtitle_track: int = -1  # -1 = off
        
        self._build_ui()
    
    def set_overlay_container(self, container: ft.Container):
        """Set the overlay container for cast dialog."""
        self._overlay_container = container
    
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
            on_track_changed=self._on_track_changed,
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
        
        # Cast button
        self._cast_btn = ft.IconButton(
            icon=ft.Icons.CAST_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            icon_size=24,
            tooltip="Cast to TV",
            on_click=self._show_cast_dialog,
        )
        
        # Mini Stop Cast Button (hidden by default)
        self._mini_stop_btn = ft.IconButton(
            icon=ft.Icons.REMOVE_FROM_QUEUE_ROUNDED,
            icon_color=ft.Colors.RED_400,
            tooltip="Stop Casting",
            visible=False,
            on_click=self._stop_casting_btn,
        )
        
        # Audio track button
        self._audio_btn = ft.IconButton(
            icon=ft.Icons.AUDIOTRACK_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            icon_size=22,
            tooltip="Audio tracks (A)",
            on_click=self._show_audio_selector,
        )
        
        # Subtitle button
        self._subtitle_btn = ft.IconButton(
            icon=ft.Icons.SUBTITLES_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            icon_size=22,
            tooltip="Subtitles (S)",
            on_click=self._show_subtitle_selector,
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
                    self._audio_btn,
                    self._subtitle_btn,
                    self._cast_btn,
                    self._mini_stop_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor="#1a1a2e",
            border_radius=10,
            visible=False,
        )
        
        # Loading indicator
        self._loading_indicator = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(
                        width=60,
                        height=60,
                        stroke_width=4,
                        color=ft.Colors.PURPLE_400,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "Loading stream...",
                        color=ft.Colors.WHITE70,
                        size=14,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor="#0a0a12",
            border_radius=16,
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
        
        # Cast Overlay Controls
        self._scan_status = ft.Text("Scanning for devices...", color=ft.Colors.WHITE70)
        self._scan_progress = ft.ProgressBar(width=400, color=ft.Colors.PURPLE_400, bgcolor=ft.Colors.WHITE10, visible=False)
        self._device_list = ft.ListView(spacing=8, padding=10)
        self._cast_status = ft.Text("", size=12, color=ft.Colors.WHITE54)
        
        # Sync Playback Toggle
        self._sync_playback_switch = ft.Switch(
            label="Play on PC too",
            value=False,
            active_color=ft.Colors.PURPLE_400,
            tooltip="Keep playing on PC while casting (Sync Playback)",
            label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        )
        
        # Casting Controls (Play/Pause, Next/Prev)
        # Casting Controls (Play/Pause, Next/Prev)
        self._cast_controls = ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.SKIP_PREVIOUS_ROUNDED, icon_color=ft.Colors.WHITE, on_click=self._cast_prev, tooltip="Previous"),
                        ft.IconButton(ft.Icons.PAUSE_ROUNDED, icon_color=ft.Colors.WHITE, on_click=self._toggle_playback, data="pause", tooltip="Play/Pause"),
                        ft.IconButton(ft.Icons.STOP_ROUNDED, icon_color=ft.Colors.RED_400, on_click=self._stop_casting_btn, tooltip="Stop Casting"),
                        ft.IconButton(ft.Icons.SKIP_NEXT_ROUNDED, icon_color=ft.Colors.WHITE, on_click=self._cast_next, tooltip="Next"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.VOLUME_DOWN_ROUNDED, icon_color=ft.Colors.WHITE70, on_click=lambda e: self.page.run_task(self._cast_volume_down), tooltip="Vol -"),
                        ft.IconButton(ft.Icons.VOLUME_OFF_ROUNDED, icon_color=ft.Colors.WHITE70, on_click=lambda e: self.page.run_task(self._cast_toggle_mute, e), data="unmuted", tooltip="Mute"),
                        ft.IconButton(ft.Icons.VOLUME_UP_ROUNDED, icon_color=ft.Colors.WHITE70, on_click=lambda e: self.page.run_task(self._cast_volume_up), tooltip="Vol +"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            visible=False,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Build layout
        self.controls = [
            self._now_playing_bar,
            ft.Container(height=8),
            self._welcome,
            self._loading_indicator,
            self._video_container,
        ]
        self.expand = True
        self.spacing = 0
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    
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
        
        # Apply system boost using wpctl (Linux only)
        if self.page and self.page.platform == ft.PagePlatform.LINUX:
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
            
    def stop(self):
        """Stop playback and reset state."""
        if self._video:
            try:
                self._video.pause()
                # Optional: seek to 0 or clear playlist
            except:
                pass
        self._is_playing = False
        self._loading_indicator.visible = False
        self._now_playing_bar.visible = False
        if self.page:
            self.page.update()
    
    def play_channel(self, channel: Channel):
        """Start playing a channel."""
        self._current_channel = channel
        
        # Update channel info text
        self._channel_info.value = channel.name
        self._now_playing_bar.visible = True
        
        # Check if we are currently casting
        if self._dlna_service.get_current_device():
            # Stop local playback if running (unless Sync is ON)
            if self._is_playing and not self._sync_playback_switch.value:
                self._video.pause()
                self._is_playing = False
                if self.page:
                    self.page.update()

            # If casting, cast to the device
            if self.page:
                self.page.run_task(self._cast_to_device, self._dlna_service.get_current_device())
            
            # If Sync is ON, we ALSO play locally
            if self._sync_playback_switch.value:
                # Fallthrough to local play logic below
                pass
            else:
                return

        # Show loading indicator, hide welcome
        self._welcome.visible = False
        self._loading_indicator.visible = True
        self._video_container.visible = False
        
        if self.page:
            self.page.update()
        
        try:
            # STOP current playback completely
            self._video.stop()
            
            # CLEAR the playlist (remove all items)
            # We do this multiple times to ensure it's empty
            for _ in range(20):
                try:
                    self._video.playlist_remove(0)
                except:
                    break
            
            # ADD the new channel as the ONLY item
            self._video.playlist_add(fv.VideoMedia(resource=channel.url))
            
            # JUMP to index 0 (the only item now)
            self._video.jump_to(0)
            
            # PLAY
            self._video.play()
            self._is_playing = True
            
            # Show video container
            self._loading_indicator.visible = False
            self._video_container.visible = True
            
            if self.page:
                self.page.update()

        except Exception as e:
            print(f"Play Error: {e}")
            self._loading_indicator.visible = False
            self._welcome.visible = True
            if self._on_error:
                self._on_error(str(e))

    
    def _on_video_loaded(self, e):
        """Handle video loaded event."""
        print(f"Video loaded! Data: {e.data if hasattr(e, 'data') else 'No Data'}")
            
        if self.page:
            self.page.update()
    
    def _on_track_changed(self, e):
        """Handle track change event - this fires when audio/subtitle tracks are detected."""
        print(f"Track Changed! Data: {e.data if hasattr(e, 'data') else 'No Data'}")
        
        # Try to parse track data if available
        if hasattr(e, 'data') and e.data:
            try:
                import json
                tracks = json.loads(e.data) if isinstance(e.data, str) else e.data
                print(f"Parsed Tracks: {tracks}")
                
                # Extract audio and subtitle tracks
                audio_tracks = []
                subtitle_tracks = []
                
                if isinstance(tracks, dict):
                    audio_tracks = tracks.get('audio', [])
                    subtitle_tracks = tracks.get('subtitle', [])
                elif isinstance(tracks, list):
                    for track in tracks:
                        if track.get('type') == 'audio':
                            audio_tracks.append(track)
                        elif track.get('type') == 'subtitle':
                            subtitle_tracks.append(track)
                
                print(f"Audio Tracks: {audio_tracks}")
                print(f"Subtitle Tracks: {subtitle_tracks}")
                
                # Update the track selector UI if tracks found
                if audio_tracks or subtitle_tracks:
                    self.set_tracks(audio_tracks, subtitle_tracks)
            except Exception as ex:
                print(f"Error parsing tracks: {ex}")
        
        if self.page:
            self.page.update()
    
    
    def _on_video_error(self, e):
        """Handle video error event."""
        if self._on_error:
            self._on_error("Failed to load stream")
            
        # Add cast button to controls if video fails

        # Check if cast button is already added to avoid duplicates
        has_cast_btn = False
        for ctrl in self.controls:
             if isinstance(ctrl, ft.Container) and isinstance(ctrl.content, ft.Row):
                  # This is likely the container we add below. Simplified check.
                  pass
        
        # We'll just retry adding if not present, but safer to just let user use the main button.
        pass

    async def _show_cast_dialog(self, e):
        """Show cast dialog using custom overlay."""
        if not self._overlay_container:
            print("No overlay container set!")
            return
            
        self._scan_status.value = "Scanning for devices..."
        self._scan_progress.visible = True
        self._device_list.controls = []
        self._cast_status.value = ""
        self._cast_controls.visible = False # Hide controls initially

        
        # Build the dialog content
        content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Cast to Device", size=20, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=ft.Colors.WHITE54,
                                on_click=lambda _: self._close_dialog()
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(color=ft.Colors.WHITE10),
                    ft.Container(
                        content=ft.Column(
                            [
                                self._scan_status, 
                                self._scan_progress,
                                self._device_list,
                                ft.Container(content=self._sync_playback_switch, padding=ft.padding.only(bottom=10)),
                                self._cast_controls, # Add controls here

                            ],
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                        height=300,  # Fixed height for list area
                    ),
                    ft.Container(
                        content=self._cast_status,
                        padding=ft.padding.only(top=10),
                    )
                ],
                spacing=10,
                tight=True,
            ),
            padding=20,
            bgcolor="#1a1a2e",
            border_radius=15,
            border=ft.border.all(1, ft.Colors.WHITE10),
            width=400,
            shadow=ft.BoxShadow(
                blur_radius=20,
                color=ft.Colors.BLACK54,
            ),
            # Center the dialog in the overlay
            alignment=ft.alignment.center,
            on_click=lambda e: None, # Prevent click propagation
        )
        
        # Set content and show overlay
        self._overlay_container.content = ft.Container(
            content=content,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.BLACK), # Dim background
            on_click=lambda _: self._close_dialog(), # Close on backdrop click
            padding=20,
        )
        self._overlay_container.visible = True
        self._overlay_container.update()
        
        # Start scanning
        await self._discover_devices()
    
    async def _discover_devices(self):
        """Discover DLNA devices."""
        if not self._device_list:
            return
        
        self._device_list.controls.clear()
        self._device_list.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=20, height=20, color=ft.Colors.PURPLE_400),
                        ft.Text("Searching for devices...", color=ft.Colors.WHITE70),
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.all(20),
            )
        )
        if self.page:
            self.page.update()
        
        # Discover devices
        self._discovered_devices = await self._dlna_service.discover_devices()
        
        self._device_list.controls.clear()
        
        if not self._discovered_devices:
            self._device_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.TV_OFF_ROUNDED, color=ft.Colors.WHITE30, size=40),
                            ft.Container(height=8),
                            ft.Text("No devices found", color=ft.Colors.WHITE54),
                            ft.Text(
                                "Make sure your TV is on and connected\nto the same network",
                                color=ft.Colors.WHITE38,
                                size=12,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(20),
                )
            )
        else:
            for device in self._discovered_devices:
                self._device_list.controls.append(self._build_device_tile(device))
        
        if self.page:
            self.page.update()
    
    def _build_device_tile(self, device: DLNADevice) -> ft.Control:
        """Build a device list tile."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.TV_ROUNDED, color=ft.Colors.PURPLE_400, size=32),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Text(device.name, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                            ft.Text(device.location.split("/")[2] if "/" in device.location else "", 
                                   color=ft.Colors.WHITE54, size=11),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CAST_CONNECTED_ROUNDED,
                        icon_color=ft.Colors.PURPLE_400,
                        tooltip="Cast to this device",
                        on_click=lambda e, d=device: self.page.run_task(self._cast_to_device, d),
                    ),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            on_click=lambda e, d=device: self.page.run_task(self._cast_to_device, d),
        )
    
    async def _cast_to_device(self, device: DLNADevice):
        """Cast current stream to device using local proxy."""
        if not self._current_channel:
            if self._cast_status:
                self._cast_status.value = "No channel is currently playing"
                self._cast_status.color = ft.Colors.RED_300
                if self.page:
                    self.page.update()
            return
        
        if self._cast_status:
            self._cast_status.value = "Starting stream proxy..."
            self._cast_status.color = ft.Colors.WHITE70
            if self.page:
                self.page.update()
        
        try:
            # Start the proxy server if not running
            if not self._stream_proxy.is_running():
                await self._stream_proxy.start()
            
            # Set the stream to proxy
            self._stream_proxy.set_stream(self._current_channel.url)
            
            # Get the proxy URL (TV will connect to this)
            proxy_url = self._stream_proxy.get_proxy_url()
            
            # Append correct extension for DLNA/TV compatibility
            # Samsung TVs often require an extension to identify content type
            lower_url = self._current_channel.url.lower()
            if ".m3u8" in lower_url:
                proxy_url += ".m3u8"
            elif ".mp4" in lower_url:
                proxy_url += ".mp4"
            elif ".mkv" in lower_url:
                proxy_url += ".mkv"
            else:
                # Default to TS for IPTV
                proxy_url += ".ts"
            
            # Use register_stream for proper ID tracking (replacing set_stream usage)
            # Actually, set_stream returns a URL now in our updated StreamProxy?
            # Let's use register_stream for safety as we updated StreamProxy to support multiple.
            # But wait, we called set_stream in line 556?
            # We should REPLACE line 556 usage with register_stream, or update this block.
            # Let's fix line 556 in previous block or here.
            # Wait, line 556 is BEFORE this chunk. I can't easily change it here without larger chunk.
            # I must check if set_stream still works.
            # In Step 785, I updated set_stream to register as 'current'.
            # So line 556 `self._stream_proxy.set_stream(self._current_channel.url)` works and sets 'current'.
            # And line 559 `get_proxy_url()` returns `.../stream/current`.
            # So my appending logic `proxy_url += ".ts"` creates `.../stream/current.ts`.
            # StreamProxy `_handle_stream` strips extension: `current` -> `current`.
            # THIS WORKS!
            
            if self._cast_status:
                self._cast_status.value = f"Casting to {device.name}..."
                if self.page:
                    self.page.update()
            
            # Cast the proxy URL to the TV
            success = await self._dlna_service.cast_to_device(
                device,
                proxy_url,
                self._current_channel.name,
            )
            
            if success:
                # Update cast button to show connected state
                self._cast_btn.icon = ft.Icons.CAST_CONNECTED_ROUNDED
                self._cast_btn.icon_color = ft.Colors.PURPLE_400
                self._mini_stop_btn.visible = True # Show mini stop button
                
                # Setup Next Channel for Gapless/Remote Control (TV Remote "Next" button)
                if self._get_next_channel:
                    try:
                        next_ch = self._get_next_channel()
                        if next_ch:
                            # Register next stream
                            next_proxy_url = self._stream_proxy.register_stream(next_ch.url)
                            
                            # Append proper extension
                            nxt_lower = next_ch.url.lower()
                            if ".m3u8" in nxt_lower:
                                next_proxy_url += ".m3u8"
                            elif ".mp4" in nxt_lower:
                                next_proxy_url += ".mp4"
                            elif ".mkv" in nxt_lower:
                                next_proxy_url += ".mkv"
                            else:
                                next_proxy_url += ".ts"
                                
                            # Set Next URI on TV
                            await self._dlna_service.set_next_av_transport_uri(next_proxy_url, next_ch.name)
                    except Exception as e:
                        print(f"Failed to set next URI: {e}")
                
                # Show success briefly then close
                if self._cast_status:
                    self._cast_status.value = f"✓ Casting to {device.name}"
                    self._cast_status.color = ft.Colors.GREEN_300
                    if self.page:
                        self.page.update()
                
                await asyncio.sleep(1.0)
                
                # Switch to "Now Casting" mode
                self._scan_status.value = f"Now Casting to {device.name}"
                self._scan_progress.visible = False
                self._device_list.controls.clear()
                self._cast_controls.visible = True
                
                # Show playing indicator
                self._device_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.CAST_CONNECTED_ROUNDED, size=64, color=ft.Colors.PURPLE_400),
                            ft.Text(self._current_channel.name, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.Text("Playing on TV", color=ft.Colors.WHITE54),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=20
                    )
                )
                
                if self.page:
                    self.page.update()
                
                return
            else:
                if self._cast_status:
                    self._cast_status.value = f"Failed to cast to {device.name}"
                    self._cast_status.color = ft.Colors.RED_300
        
        except Exception as e:
            if self._cast_status:
                self._cast_status.value = f"Error: {str(e)}"
                self._cast_status.color = ft.Colors.RED_300
        
        if self.page:
            self.page.update()
    
    async def _toggle_playback(self, e):
        """Toggle Play/Pause on DLNA device."""
        if not self._dlna_service:
            return
            
        icon_btn = e.control
        is_pause = icon_btn.data == "pause"
        
        if is_pause:
            success = await self._dlna_service.pause_stream()
            if success:
                icon_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
                icon_btn.data = "play"
        else:
            success = await self._dlna_service.resume_stream()
            if success:
                icon_btn.icon = ft.Icons.PAUSE_ROUNDED
                icon_btn.data = "pause"
        
        if self.page:
            self.page.update()

    async def _stop_casting_btn(self, e):
        """Stop casting and close dialog."""
        if self._dlna_service:
            await self._dlna_service.stop_casting()
        
        # Stop the proxy to clear streams/resources
        if self._stream_proxy:
            await self._stream_proxy.stop()
            
        
        if self._stream_proxy:
            await self._stream_proxy.stop()
            
        
        self._cast_btn.icon = ft.Icons.CAST_ROUNDED
        self._cast_btn.icon_color = ft.Colors.WHITE70
        self._mini_stop_btn.visible = False # Hide mini stop button
        
        # If the dialog is open, close it.
        if self._overlay_container and self._overlay_container.visible:
            self._close_dialog()
            
        if self.page:
            self.page.update()
        
    async def _cast_next(self, e):
        """Cast next channel."""
        if self._on_next:
            self._on_next()

    async def _cast_prev(self, e):
        """Cast previous channel."""
        if self._on_prev:
            self._on_prev()

    async def _cast_volume_up(self):
        """Increase cast volume."""
        if not self._dlna_service: return
        
        try:
            current_vol = await self._dlna_service.get_volume()
            new_vol = min(100, current_vol + 5)
            await self._dlna_service.set_volume(new_vol)
        except Exception:
            pass

    async def _cast_volume_down(self):
        """Decrease cast volume."""
        if not self._dlna_service: return
        
        try:
            current_vol = await self._dlna_service.get_volume()
            new_vol = max(0, current_vol - 5)
            await self._dlna_service.set_volume(new_vol)
        except Exception:
            pass

    async def _cast_toggle_mute(self, e):
        """Toggle mute on cast device."""
        if not self._dlna_service: return
        
        icon = e.control
        is_muted = icon.data == "muted"
        
        # Toggle
        new_mute = not is_muted
        success = await self._dlna_service.set_mute(new_mute)
        
        if success:
            if new_mute:
                icon.icon = ft.Icons.VOLUME_OFF_ROUNDED
                icon.icon_color = ft.Colors.RED_400
                icon.data = "muted"
            else:
                icon.icon = ft.Icons.VOLUME_UP_ROUNDED
                icon.icon_color = ft.Colors.WHITE70
                icon.data = "unmuted"
            if self.page:
                self.page.update()

    def _close_dialog(self):
        """Close the cast overlay."""
        if self._overlay_container:
            self._overlay_container.visible = False
            self._overlay_container.content = None
            self._overlay_container.update()
            
        # Clear references
        self._cast_status.value = ""
        self._cast_status.color = ft.Colors.WHITE70

    def _show_audio_selector(self, e):
        """Show audio track selector."""
        if not self._overlay_container:
            return
        
        # Get tracks from current channel if available
        tracks = self._audio_tracks
        if self._current_channel and hasattr(self._current_channel, 'audio_tracks'):
            tracks = self._current_channel.audio_tracks or []
        
        # If no tracks detected, show some mock tracks for demo
        if not tracks:
            tracks = [
                {"language": "und", "codec": "aac", "channels": 2},
            ]
        
        selector = TrackSelector(
            track_type="audio",
            tracks=tracks,
            current_track=self._current_audio_track,
            on_track_select=self._on_audio_track_select,
            on_close=self._close_track_selector,
        )
        
        self._overlay_container.content = selector
        self._overlay_container.visible = True
        if self.page:
            self._overlay_container.update()
    
    def _show_subtitle_selector(self, e):
        """Show subtitle track selector."""
        if not self._overlay_container:
            return
        
        # Get tracks from current channel if available
        tracks = self._subtitle_tracks
        if self._current_channel and hasattr(self._current_channel, 'subtitle_tracks'):
            tracks = self._current_channel.subtitle_tracks or []
        
        selector = TrackSelector(
            track_type="subtitle",
            tracks=tracks,
            current_track=self._current_subtitle_track,
            on_track_select=self._on_subtitle_track_select,
            on_close=self._close_track_selector,
        )
        
        self._overlay_container.content = selector
        self._overlay_container.visible = True
        if self.page:
            self._overlay_container.update()
    
    def _on_audio_track_select(self, track_index: int):
        """Handle audio track selection."""
        self._current_audio_track = track_index
        
        # Update button appearance
        if track_index >= 0:
            self._audio_btn.icon_color = "#6366f1"  # Purple when active
        else:
            self._audio_btn.icon_color = ft.Colors.WHITE70
        
        # Note: Actual track switching requires flet_video support or 
        # external player integration (ffmpeg, VLC). For now we update state.
        # In a full implementation, you would call:
        # self._video.set_audio_track(track_index)
        
        if self.page:
            self.page.update()
    
    def _on_subtitle_track_select(self, track_index: int):
        """Handle subtitle track selection."""
        self._current_subtitle_track = track_index
        
        # Update button appearance
        if track_index >= 0:
            self._subtitle_btn.icon_color = "#22c55e"  # Green when active
        else:
            self._subtitle_btn.icon_color = ft.Colors.WHITE70
        
        # Note: Actual subtitle switching requires flet_video support or
        # external subtitle rendering. For now we update state.
        # In a full implementation, you would call:
        # self._video.set_subtitle_track(track_index)
        
        if self.page:
            self.page.update()
    
    def _close_track_selector(self):
        """Close track selector overlay."""
        if self._overlay_container:
            self._overlay_container.visible = False
            self._overlay_container.content = None
            if self.page:
                self._overlay_container.update()
    
    def set_tracks(self, audio_tracks: List[dict] = None, subtitle_tracks: List[dict] = None):
        """Set available tracks for the current stream."""
        if audio_tracks is not None:
            self._audio_tracks = audio_tracks
        if subtitle_tracks is not None:
            self._subtitle_tracks = subtitle_tracks
