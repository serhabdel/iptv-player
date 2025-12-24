"""Track selector component for audio and subtitle selection."""
import flet as ft
from typing import Optional, Callable, List


class TrackSelector(ft.Container):
    """Audio and subtitle track selector overlay."""
    
    def __init__(
        self,
        track_type: str = "audio",  # "audio" or "subtitle"
        tracks: List[dict] = None,
        current_track: int = 0,
        on_track_select: Optional[Callable[[int], None]] = None,
        on_close: Optional[Callable] = None,
    ):
        super().__init__()
        self.track_type = track_type
        self.tracks = tracks or []
        self.current_track = current_track
        self._on_track_select = on_track_select
        self._on_close = on_close
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the track selector UI."""
        # Title configuration
        if self.track_type == "audio":
            title = "Audio Tracks"
            icon = ft.Icons.AUDIOTRACK_ROUNDED
            color = "#6366f1"
            empty_message = "No audio tracks available"
        else:
            title = "Subtitles"
            icon = ft.Icons.SUBTITLES_ROUNDED
            color = "#22c55e"
            empty_message = "No subtitles available"
        
        # Track list
        track_items = []
        
        if self.track_type == "subtitle":
            # Add "Off" option for subtitles
            off_item = self._build_track_item(
                index=-1,
                label="Off",
                sublabel="Disable subtitles",
                is_selected=self.current_track == -1,
            )
            track_items.append(off_item)
        
        if not self.tracks:
            track_items.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.INFO_OUTLINE_ROUNDED,
                                size=32,
                                color=ft.Colors.WHITE38,
                            ),
                            ft.Text(
                                empty_message,
                                size=14,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=24,
                    alignment=ft.alignment.center,
                )
            )
        else:
            for i, track in enumerate(self.tracks):
                label = self._get_track_label(track)
                sublabel = self._get_track_sublabel(track)
                item = self._build_track_item(
                    index=i,
                    label=label,
                    sublabel=sublabel,
                    is_selected=i == self.current_track,
                )
                track_items.append(item)
        
        # Header
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=24, color=color),
                    ft.Text(
                        title,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        icon_size=20,
                        icon_color=ft.Colors.WHITE70,
                        on_click=lambda e: self._on_close() if self._on_close else None,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.only(left=20, right=8, top=12, bottom=12),
            border=ft.border.only(bottom=ft.BorderSide(1, "#2a2a3e")),
        )
        
        # Track list
        track_list = ft.Container(
            content=ft.Column(
                track_items,
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=12,
            expand=True,
        )
        
        # Keyboard hints
        hints = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text("↑↓", size=10, color=ft.Colors.WHITE),
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    bgcolor="#3a3a4e",
                                    border_radius=4,
                                ),
                                ft.Text("Navigate", size=11, color=ft.Colors.WHITE54),
                            ],
                            spacing=6,
                        ),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text("Enter", size=10, color=ft.Colors.WHITE),
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    bgcolor="#3a3a4e",
                                    border_radius=4,
                                ),
                                ft.Text("Select", size=11, color=ft.Colors.WHITE54),
                            ],
                            spacing=6,
                        ),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text("Esc", size=10, color=ft.Colors.WHITE),
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    bgcolor="#3a3a4e",
                                    border_radius=4,
                                ),
                                ft.Text("Close", size=11, color=ft.Colors.WHITE54),
                            ],
                            spacing=6,
                        ),
                    ),
                ],
                spacing=16,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor="#1a1a2e",
            border=ft.border.only(top=ft.BorderSide(1, "#2a2a3e")),
        )
        
        self.content = ft.Container(
            content=ft.Column(
                [
                    header,
                    track_list,
                    hints,
                ],
                spacing=0,
                expand=True,
            ),
            width=350,
            height=400,
            bgcolor="#0f0f1a",
            border_radius=16,
            border=ft.border.all(1, "#2a2a3e"),
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=20,
                color="#00000080",
            ),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        self.alignment = ft.alignment.center
        self.expand = True
        self.bgcolor = "#00000080"  # Semi-transparent backdrop
        self.on_click = lambda e: self._on_close() if self._on_close else None
    
    def _build_track_item(
        self,
        index: int,
        label: str,
        sublabel: str,
        is_selected: bool,
    ) -> ft.Container:
        """Build a track item."""
        
        def on_click(e):
            if self._on_track_select:
                self._on_track_select(index)
            if self._on_close:
                self._on_close()
        
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.CHECK_CIRCLE_ROUNDED if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                            size=20,
                            color="#6366f1" if is_selected else ft.Colors.WHITE38,
                        ),
                        width=32,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                label,
                                size=14,
                                color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE70,
                                weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL,
                            ),
                            ft.Text(
                                sublabel,
                                size=11,
                                color=ft.Colors.WHITE54,
                            ) if sublabel else ft.Container(),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor="#6366f120" if is_selected else "transparent",
            border=ft.border.all(1, "#6366f1") if is_selected else None,
            on_click=on_click,
            ink=True,
        )
    
    def _get_track_label(self, track: dict) -> str:
        """Get display label for a track."""
        # Language mapping
        lang_map = {
            "en": "English",
            "eng": "English",
            "fr": "French",
            "fra": "French",
            "fre": "French",
            "es": "Spanish",
            "spa": "Spanish",
            "de": "German",
            "deu": "German",
            "ger": "German",
            "ar": "Arabic",
            "ara": "Arabic",
            "it": "Italian",
            "ita": "Italian",
            "pt": "Portuguese",
            "por": "Portuguese",
            "ru": "Russian",
            "rus": "Russian",
            "ja": "Japanese",
            "jpn": "Japanese",
            "ko": "Korean",
            "kor": "Korean",
            "zh": "Chinese",
            "chi": "Chinese",
            "zho": "Chinese",
            "nl": "Dutch",
            "nld": "Dutch",
            "dut": "Dutch",
            "pl": "Polish",
            "pol": "Polish",
            "tr": "Turkish",
            "tur": "Turkish",
            "hi": "Hindi",
            "hin": "Hindi",
            "und": "Undetermined",
        }
        
        lang = track.get("language", track.get("lang", ""))
        if lang.lower() in lang_map:
            return lang_map[lang.lower()]
        
        # Try title or name
        if track.get("title"):
            return track["title"]
        if track.get("name"):
            return track["name"]
        
        # Return language code if nothing else
        return lang.upper() if lang else f"Track {track.get('index', '?')}"
    
    def _get_track_sublabel(self, track: dict) -> str:
        """Get sublabel with technical details."""
        parts = []
        
        if self.track_type == "audio":
            # Codec
            codec = track.get("codec", track.get("codec_name", ""))
            if codec:
                parts.append(codec.upper())
            
            # Channels
            channels = track.get("channels", track.get("channel_layout", ""))
            if channels:
                if isinstance(channels, int):
                    channel_names = {1: "Mono", 2: "Stereo", 6: "5.1", 8: "7.1"}
                    parts.append(channel_names.get(channels, f"{channels}ch"))
                else:
                    parts.append(str(channels))
            
            # Bitrate
            bitrate = track.get("bitrate", track.get("bit_rate", 0))
            if bitrate:
                kbps = int(bitrate) // 1000 if int(bitrate) > 1000 else int(bitrate)
                parts.append(f"{kbps} kbps")
        
        else:  # subtitle
            # Type
            sub_type = track.get("type", track.get("codec_name", ""))
            if sub_type:
                type_names = {
                    "subrip": "SRT",
                    "srt": "SRT",
                    "ass": "ASS",
                    "ssa": "SSA",
                    "mov_text": "MOV Text",
                    "hdmv_pgs_subtitle": "PGS",
                    "dvd_subtitle": "DVD",
                    "webvtt": "WebVTT",
                }
                parts.append(type_names.get(sub_type.lower(), sub_type.upper()))
            
            # Forced/Default flags
            if track.get("forced"):
                parts.append("Forced")
            if track.get("default"):
                parts.append("Default")
        
        return " • ".join(parts) if parts else ""
    
    def set_tracks(self, tracks: List[dict], current: int = 0):
        """Update tracks and rebuild UI."""
        self.tracks = tracks
        self.current_track = current
        self._build_ui()
        self.update()
