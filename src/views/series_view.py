"""Series view for displaying seasons and episodes."""
import flet as ft
from typing import Optional, Callable, Dict, List
from ..models.channel import Channel
from ..services.state_manager import StateManager


class SeriesView(ft.Container):
    """View to display series details, seasons, and episodes."""
    
    def __init__(
        self,
        state_manager: StateManager,
        on_back: Optional[Callable] = None,
        on_play_episode: Optional[Callable[[Channel], None]] = None,
    ):
        super().__init__()
        self.state = state_manager
        self._on_back = on_back
        self._on_play_episode = on_play_episode
        
        # Series data
        self._series_name: str = ""
        self._episodes: List[Channel] = []
        self._seasons: Dict[int, List[Channel]] = {}
        self._sorted_seasons: List[int] = []  # Keep track of seasons in order
        self._selected_season: int = 1
        
        # UI Components
        self._header_content = ft.Container()
        self._season_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[],
            on_change=self._on_season_change,
            scrollable=True,
            divider_color=ft.Colors.TRANSPARENT,
            indicator_color=ft.Colors.PURPLE_400,
            label_color=ft.Colors.WHITE,
            unselected_label_color=ft.Colors.WHITE54,
        )
        self._episode_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        
        self._build_ui()
        
    def _build_ui(self):
        """Build the basic UI structure."""
        self.content = ft.Column(
            [
                # Header with back button
                ft.Container(
                    content=ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                on_click=lambda e: self._on_back() if self._on_back else None,
                            ),
                            ft.Text("Back", color=ft.Colors.WHITE70),
                        ],
                    ),
                    padding=ft.padding.only(left=8, top=8),
                ),
                
                # Series Info Header
                self._header_content,
                
                # Content Area (Seasons + Episodes)
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                content=self._season_tabs,
                                border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.WHITE10)),
                            ),
                            ft.Container(height=10),
                            ft.Container(
                                content=self._episode_list,
                                expand=True,
                            ),
                        ],
                        expand=True,
                    ),
                    expand=True,
                    padding=16,
                ),
            ],
            spacing=0,
            expand=True,
        )
        self.expand = True
        self.bgcolor = "#0a0a12" # Matches app background

    def load_series(self, series_name: str, episodes: List[Channel]):
        """Load series data and group by season."""
        self._series_name = series_name
        self._episodes = episodes
        
        # Group by season
        self._seasons = {}
        unknown_season = []
        
        for ep in episodes:
            if ep.season:
                if ep.season not in self._seasons:
                    self._seasons[ep.season] = []
                self._seasons[ep.season].append(ep)
            else:
                unknown_season.append(ep)
        
        # Add unknown season as Season 1 if it's the only one, or "Extras"
        if unknown_season:
            if not self._seasons:
                self._seasons[1] = unknown_season
            else:
                self._seasons[0] = unknown_season # 0 for Extras/Unknown
        
        # Sort seasons and store the list
        self._sorted_seasons = sorted(self._seasons.keys())
        if not self._sorted_seasons:
            self._sorted_seasons = [1]
            self._seasons = {1: []}
            
        self._selected_season = self._sorted_seasons[0]
        
        # update UI
        self._update_header()
        self._update_season_tabs()
        self._update_episode_list()
        
        if self.page:
            self.update()

    def _update_header(self):
        """Update the series header info."""
        # Find a high quality logo from episodes
        logo = None
        for ep in self._episodes:
            if ep.logo:
                logo = ep.logo
                break
                
        self._header_content.content = ft.Container(
            content=ft.Row(
                [
                    # Poster
                    ft.Container(
                        content=ft.Image(
                            src=logo if logo else "",
                            width=150,
                            height=220,
                            fit=ft.ImageFit.COVER,
                            error_content=ft.Icon(ft.Icons.TV_ROUNDED, size=50, color=ft.Colors.WHITE24),
                        ) if logo else ft.Icon(ft.Icons.TV_ROUNDED, size=50, color=ft.Colors.WHITE24),
                        width=150,
                        height=220,
                        border_radius=12,
                        bgcolor="#1a1a2e",
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        animate_opacity=300,
                    ),
                    # Info
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    self._series_name,
                                    size=32,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Text(f"{len(self._seasons)} Seasons", size=12, color=ft.Colors.WHITE),
                                            bgcolor=ft.Colors.WHITE10,
                                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                            border_radius=4,
                                        ),
                                        ft.Container(
                                            content=ft.Text(f"{len(self._episodes)} Episodes", size=12, color=ft.Colors.WHITE),
                                            bgcolor=ft.Colors.WHITE10,
                                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                            border_radius=4,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                ft.Container(height=10),
                                ft.ElevatedButton(
                                    "Play S1 E1",
                                    icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                    style=ft.ButtonStyle(
                                        color=ft.Colors.WHITE,
                                        bgcolor=ft.Colors.PURPLE_600,
                                        padding=20,
                                    ),
                                    on_click=self._play_first_episode,
                                ),
                            ],
                            spacing=10,
                        ),
                        expand=True,
                        padding=ft.padding.only(left=20),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#1a1a2e", "#0a0a12"],
            ),
        )

    def _update_season_tabs(self):
        """Update season selection tabs."""
        self._season_tabs.tabs = []
        for season_num in self._sorted_seasons:
            title = f"Season {season_num}" if season_num > 0 else "Extras"
            self._season_tabs.tabs.append(
                ft.Tab(
                    tab_content=ft.Text(title, size=16, weight=ft.FontWeight.W_500),
                )
            )
        self._season_tabs.selected_index = 0

    def _on_season_change(self, e):
        """Handle season tab change."""
        try:
            # Map tab index to actual season number from sorted list
            tab_index = self._season_tabs.selected_index
            if 0 <= tab_index < len(self._sorted_seasons):
                self._selected_season = self._sorted_seasons[tab_index]
                self._update_episode_list()
                if self.page:
                    self.update()
        except Exception as ex:
            print(f"Error changing season: {ex}")

    def _update_episode_list(self):
        """Update list of episodes for selected season."""
        self._episode_list.controls = []
        
        episodes = self._seasons.get(self._selected_season, [])
        # Sort by episode number if available
        episodes.sort(key=lambda x: x.episode if x.episode else 999)
        
        for ep in episodes:
            self._episode_list.controls.append(self._create_episode_item(ep))

    def _create_episode_item(self, episode: Channel) -> ft.Container:
        """Create a list item for an episode."""
        # Build episode label: SxxExx format using current selected season
        season_num = episode.season if episode.season else self._selected_season
        ep_num = episode.episode
        
        if season_num and ep_num:
            ep_label = f"S{season_num:02d}E{ep_num:02d}"
        elif ep_num:
            ep_label = f"E{ep_num}"
        else:
            ep_label = ""
        
        # Get clean episode name (strip any existing SxxExx patterns)
        name = episode.name
        # Remove SxxExx pattern from name if present
        import re
        name = re.sub(r'S\d{1,2}E\d{1,2}\s*[-:]?\s*', '', name, flags=re.IGNORECASE).strip()
             
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED, color=ft.Colors.WHITE70),
                        padding=10,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                f"{ep_label} - {name}" if ep_label else name,
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.WHITE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                "Watched" if episode.last_watched else "Not watched",
                                size=12,
                                color=ft.Colors.GREEN_400 if episode.last_watched else ft.Colors.WHITE24,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                         icon=ft.Icons.FAVORITE_ROUNDED if episode.is_favorite else ft.Icons.FAVORITE_BORDER_ROUNDED,
                         icon_color=ft.Colors.PINK_400 if episode.is_favorite else ft.Colors.WHITE24,
                         icon_size=20,
                         on_click=lambda e: self._toggle_favorite(e, episode)
                    )
                ],
            ),
            padding=ft.padding.symmetric(vertical=8, horizontal=10),
            border_radius=8,
            bgcolor=ft.Colors.WHITE10 if episode.is_favorite else "#1a1a2e",
            on_click=lambda e: self._on_play_episode(episode) if self._on_play_episode else None,
            ink=True,
        )
        
    def _toggle_favorite(self, e, episode):
        """Toggle favorite status."""
        e.control.icon = ft.Icons.FAVORITE_BORDER_ROUNDED if episode.is_favorite else ft.Icons.FAVORITE_ROUNDED
        e.control.icon_color = ft.Colors.WHITE24 if episode.is_favorite else ft.Colors.PINK_400
        episode.is_favorite = not episode.is_favorite
        self.state.toggle_favorite(episode)
        e.control.update()

    def _play_first_episode(self, e):
        """Play S1 E1."""
        # Find first season
        sorted_seasons = sorted(self._seasons.keys())
        first_season = self._seasons.get(sorted_seasons[0], [])
        if first_season:
             # Find first episode (sorted by episode num)
             first_season.sort(key=lambda x: x.episode if x.episode else 999)
             if self._on_play_episode:
                 self._on_play_episode(first_season[0])
