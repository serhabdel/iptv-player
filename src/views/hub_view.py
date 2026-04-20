"""Hub view - Main navigation hub with content type cards."""
import flet as ft
from typing import Optional, Callable
from ..services.state_manager import StateManager


class HubView(ft.Container):
    """Main hub navigation view with content type cards."""
    
    def __init__(
        self,
        state_manager: StateManager,
        on_hub_select: Optional[Callable[[str], None]] = None,
        on_settings_click: Optional[Callable] = None,
        on_play_channel: Optional[Callable] = None,
    ):
        super().__init__()
        self.state = state_manager
        self._on_hub_select = on_hub_select
        self._on_settings_click = on_settings_click
        self._on_play_channel = on_play_channel
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the hub view UI."""
        # Get content counts from classification
        counts = self.state.get_content_counts()
        
        # Hub cards configuration
        hubs = [
            {
                "id": "live",
                "title": "Live TV",
                "icon": ft.Icons.LIVE_TV_ROUNDED,
                "count": counts.get("live", 0),
                "subtitle": "Channels",
                "gradient": [("#6366f1", "#8b5cf6"), ("#4f46e5", "#7c3aed")],
                "description": "Watch live television channels"
            },
            {
                "id": "movie",
                "title": "Movies",
                "icon": ft.Icons.MOVIE_ROUNDED,
                "count": counts.get("movie", 0),
                "subtitle": "Movies",
                "gradient": [("#ec4899", "#f43f5e"), ("#db2777", "#e11d48")],
                "description": "Browse and watch movies"
            },
            {
                "id": "series",
                "title": "Series",
                "icon": ft.Icons.TV_ROUNDED,
                "count": counts.get("series", 0),
                "subtitle": "TV Shows",
                "gradient": [("#14b8a6", "#22c55e"), ("#0d9488", "#16a34a")],
                "description": "Watch TV series and episodes"
            },
            {
                "id": "settings",
                "title": "Settings",
                "icon": ft.Icons.SETTINGS_ROUNDED,
                "count": None,
                "subtitle": None,
                "gradient": [("#64748b", "#475569"), ("#475569", "#334155")],
                "description": "Configure your preferences"
            },
        ]
        
        # Create hub cards
        hub_cards = []
        for hub in hubs:
            card = self._create_hub_card(hub)
            hub_cards.append(card)
        
        # Header
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.HOME_ROUNDED, size=32, color="#a78bfa"),
                    ft.Text(
                        "IPTV Player",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                ],
                spacing=12,
            ),
            margin=ft.margin.only(bottom=8),
        )
        
        # Welcome message
        welcome = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Welcome Back!",
                        size=20,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.WHITE70,
                    ),
                    ft.Text(
                        "Select a category to start watching",
                        size=14,
                        color=ft.Colors.WHITE54,
                    ),
                ],
                spacing=4,
            ),
            margin=ft.margin.only(bottom=24),
        )
        
        # Hub cards grid
        cards_grid = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        hub_cards[:2],
                        spacing=20,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        hub_cards[2:],
                        spacing=20,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
        )
        
        # Continue watching section (movies/series with saved positions)
        continue_watching = self._build_continue_watching_section()
        
        # Favorites section (if any)
        favorites_section = self._build_favorites_section()
        
        # Recently viewed section (if any)
        recently_viewed = self._build_recently_viewed_section()
        
        # Main content
        self.content = ft.Container(
            content=ft.Column(
                [
                    header,
                    welcome,
                    cards_grid,
                    continue_watching if continue_watching else ft.Container(),
                    favorites_section if favorites_section else ft.Container(),
                    recently_viewed if recently_viewed else ft.Container(),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            expand=True,
            padding=40,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=["#0f0f1a", "#1a1a2e", "#16162a"],
            ),
        )
        self.expand = True
    
    def _create_hub_card(self, hub: dict) -> ft.Container:
        """Create a hub card with premium styling."""
        hub_id = hub["id"]
        is_settings = hub_id == "settings"
        
        # Count display
        count_content = []
        if hub["count"] is not None and hub["count"] > 0:
            count_content = [
                ft.Text(
                    f"{hub['count']:,}",
                    size=36,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                ft.Text(
                    hub["subtitle"],
                    size=12,
                    color=ft.Colors.WHITE70,
                ),
            ]
        elif hub["count"] == 0 and not is_settings:
            count_content = [
                ft.Text(
                    "No content",
                    size=14,
                    color=ft.Colors.WHITE54,
                    italic=True,
                ),
            ]
        
        def on_hover(e):
            if e.data == "true":
                card.scale = 1.02
                card.shadow = ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=20,
                    color=hub["gradient"][0][0] + "40",
                )
            else:
                card.scale = 1.0
                card.shadow = ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=10,
                    color="#00000040",
                )
            card.update()
        
        def on_click(e):
            if is_settings and self._on_settings_click:
                self._on_settings_click()
            elif self._on_hub_select:
                self._on_hub_select(hub_id)
        
        card = ft.Container(
            content=ft.Column(
                [
                    # Icon
                    ft.Container(
                        content=ft.Icon(
                            hub["icon"],
                            size=48,
                            color=ft.Colors.WHITE,
                        ),
                        margin=ft.margin.only(bottom=16),
                    ),
                    # Title
                    ft.Text(
                        hub["title"],
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                    # Count or description
                    ft.Column(
                        count_content if count_content else [
                            ft.Text(
                                hub["description"],
                                size=12,
                                color=ft.Colors.WHITE54,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=280,
            height=200,
            padding=24,
            border_radius=20,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[hub["gradient"][0][0], hub["gradient"][0][1]],
            ),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color="#00000040",
            ),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=on_hover,
            on_click=on_click,
            ink=True,
        )
        
        return card
    
    def _format_duration(self, ms: int) -> str:
        """Format milliseconds as H:MM:SS or MM:SS."""
        total_seconds = ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    
    def _build_continue_watching_section(self) -> Optional[ft.Container]:
        """Build continue watching section with progress bars."""
        items = self.state.get_continue_watching(limit=10)
        if not items:
            return None
        
        tiles = []
        for item in items:
            progress = item["progress"] / 100.0  # 0.0 to 1.0
            pos_str = self._format_duration(item["position_ms"])
            dur_str = self._format_duration(item["duration_ms"])
            
            content_icon = ft.Icons.MOVIE_ROUNDED if item["content_type"] == "movie" else ft.Icons.TV_ROUNDED
            
            tile = ft.Container(
                content=ft.Column(
                    [
                        # Thumbnail / icon
                        ft.Container(
                            content=ft.Image(
                                src=item["logo"],
                                width=120,
                                height=70,
                                fit=ft.BoxFit.COVER,
                                border_radius=6,
                                error_content=ft.Container(
                                    content=ft.Icon(content_icon, size=28, color=ft.Colors.WHITE24),
                                    alignment=ft.Alignment.CENTER,
                                ),
                            ) if item.get("logo") else ft.Container(
                                content=ft.Icon(content_icon, size=28, color=ft.Colors.WHITE24),
                                alignment=ft.Alignment.CENTER,
                            ),
                            width=120,
                            height=70,
                            bgcolor="#2a2a3e",
                            border_radius=6,
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        ),
                        # Progress bar
                        ft.ProgressBar(
                            value=progress,
                            width=120,
                            height=3,
                            color="#a78bfa",
                            bgcolor=ft.Colors.WHITE10,
                        ),
                        # Title
                        ft.Text(
                            item["name"][:20] + "..." if len(item["name"]) > 20 else item["name"],
                            size=11,
                            color=ft.Colors.WHITE,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            weight=ft.FontWeight.W_500,
                        ),
                        # Time info
                        ft.Text(
                            f"{pos_str} / {dur_str}",
                            size=10,
                            color=ft.Colors.WHITE38,
                        ),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=130,
                padding=8,
                border_radius=10,
                bgcolor="#1a1a2e",
                on_click=lambda e, url=item["url"]: self._play_continue_watching(url),
                on_hover=lambda e: self._on_tile_hover(e),
                ink=True,
            )
            tiles.append(tile)
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED, size=20, color="#a78bfa"),
                            ft.Text(
                                "Continue Watching",
                                size=16,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                f"({len(items)})",
                                size=14,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        tiles,
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ],
                spacing=12,
            ),
            margin=ft.margin.only(top=24),
            padding=16,
            border_radius=12,
            bgcolor="#1a1a2e40",
            border=ft.border.all(1, "#a78bfa20"),
        )
    
    def _play_continue_watching(self, url: str):
        """Play a continue watching item (will auto-resume from saved position)."""
        channels = self.state.get_all_channels()
        for channel in channels:
            if channel.url == url:
                if self._on_play_channel:
                    self._on_play_channel(channel)
                break
    
    def _build_favorites_section(self) -> Optional[ft.Container]:
        """Build favorites section if there are items."""
        favorites = self.state.get_favorites()
        
        if not favorites:
            return None
        
        # Create favorite tiles (show up to 8)
        tiles = []
        for channel in favorites[:8]:
            # Determine icon based on content type
            icon_map = {
                "live": ft.Icons.LIVE_TV_ROUNDED,
                "movie": ft.Icons.MOVIE_ROUNDED,
                "series": ft.Icons.TV_ROUNDED,
            }
            content_type = getattr(channel, 'content_type', 'live')
            icon = icon_map.get(content_type, ft.Icons.PLAY_CIRCLE_FILL_ROUNDED)
            
            tile = ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(
                                icon,
                                size=28,
                                color=ft.Colors.WHITE70,
                            ) if not channel.logo else ft.Image(
                                src=channel.logo,
                                width=70,
                                height=50,
                                fit=ft.BoxFit.COVER,
                                border_radius=6,
                            ),
                            width=70,
                            height=50,
                            bgcolor="#2a2a3e",
                            border_radius=6,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(
                            channel.name[:18] + "..." if len(channel.name) > 18 else channel.name,
                            size=11,
                            color=ft.Colors.WHITE70,
                            text_align=ft.TextAlign.CENTER,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                ),
                width=90,
                padding=8,
                border_radius=10,
                bgcolor="#1a1a2e",
                on_click=lambda e, ch=channel: self._play_favorite(ch),
                on_hover=lambda e: self._on_tile_hover(e),
                ink=True,
            )
            tiles.append(tile)
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.FAVORITE_ROUNDED, size=20, color="#f472b6"),
                            ft.Text(
                                "Favorites",
                                size=16,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                f"({len(favorites)})",
                                size=14,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        tiles,
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ],
                spacing=12,
            ),
            margin=ft.margin.only(top=24),
            padding=16,
            border_radius=12,
            bgcolor="#1a1a2e40",
            border=ft.border.all(1, "#f472b620"),
        )
    
    def _play_favorite(self, channel):
        """Play a favorite channel directly."""
        if self._on_play_channel:
            self._on_play_channel(channel)
        elif self._on_hub_select:
            # Fallback: navigate to content type
            content_type = getattr(channel, 'content_type', 'live')
            self._on_hub_select(content_type)
    
    def _on_tile_hover(self, e):
        """Handle hover effect on tiles."""
        if e.data == "true":
            e.control.bgcolor = "#2a2a4e"
        else:
            e.control.bgcolor = "#1a1a2e"
        e.control.update()
    
    def _build_recently_viewed_section(self) -> Optional[ft.Container]:
        """Build recently viewed section if there are items."""
        recent = self.state.get_recently_viewed(limit=10)
        
        if not recent:
            return None
        
        # Create recently viewed tiles
        tiles = []
        for item in recent[:6]:
            tile = ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.PLAY_CIRCLE_FILL_ROUNDED,
                                size=32,
                                color=ft.Colors.WHITE70,
                            ) if not item.get("logo") else ft.Image(
                                src=item.get("logo"),
                                width=60,
                                height=40,
                                fit=ft.BoxFit.COVER,
                                border_radius=4,
                            ),
                            width=60,
                            height=40,
                            bgcolor="#2a2a3e",
                            border_radius=4,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(
                            item.get("name", "Unknown")[:15] + "..." if len(item.get("name", "")) > 15 else item.get("name", "Unknown"),
                            size=11,
                            color=ft.Colors.WHITE70,
                            text_align=ft.TextAlign.CENTER,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                width=80,
                padding=8,
                border_radius=8,
                on_click=lambda e, url=item.get("url"): self._play_recently_viewed(url),
                ink=True,
            )
            tiles.append(tile)
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.HISTORY_ROUNDED, size=20, color="#a78bfa"),
                            ft.Text(
                                "Recently Viewed",
                                size=16,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        tiles,
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ],
                spacing=12,
            ),
            margin=ft.margin.only(top=32),
            padding=16,
            border_radius=12,
            bgcolor="#1a1a2e40",
        )
    
    def _play_recently_viewed(self, url: str):
        """Play a recently viewed item directly."""
        # Find channel by URL and play directly
        channels = self.state.get_all_channels()
        for channel in channels:
            if channel.url == url:
                if self._on_play_channel:
                    # Play directly
                    self._on_play_channel(channel)
                elif self._on_hub_select:
                    # Fallback: Navigate to appropriate content type
                    content_type = getattr(channel, 'content_type', 'live')
                    self._on_hub_select(content_type)
                break
    
    def refresh(self):
        """Refresh the view."""
        self._build_ui()
        if self.page:
            self.update()
