"""Channel list component with categories and search - optimized for large playlists."""
import flet as ft
from typing import List, Optional, Callable
from ..models.channel import Channel


class ChannelList(ft.Container):
    """Channel list component with lazy loading for large playlists (8K+ channels)."""
    
    # Number of items to load at a time
    PAGE_SIZE = 50
    
    def __init__(
        self,
        channels: List[Channel] = None,
        groups: List[str] = None,
        on_channel_select: Optional[Callable[[Channel], None]] = None,
        on_favorite_toggle: Optional[Callable[[Channel], None]] = None,
    ):
        super().__init__()
        self._channels = channels or []
        self._groups = groups or []
        self._filtered_channels: List[Channel] = []
        self._displayed_count = 0
        self._on_channel_select = on_channel_select
        self._on_favorite_toggle = on_favorite_toggle
        self._selected_channel: Optional[Channel] = None
        self._selected_group: Optional[str] = None
        self._search_query = ""
        self._show_favorites_only = False
        self._content_type = "all"
        self._is_updating = False  # Prevent concurrent updates
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the channel list UI."""
        self._search_field = ft.TextField(
            hint_text="Search channels...",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            border_radius=30,
            height=48,
            text_size=14,
            content_padding=ft.padding.only(left=12, right=12),
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.PURPLE_400,
            bgcolor="#1a1a2e",
            hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
            color=ft.Colors.WHITE,
            on_submit=self._on_search_submit,  # Only search on Enter
        )
        
        self._search_btn = ft.IconButton(
            icon=ft.Icons.SEARCH_ROUNDED,
            icon_color=ft.Colors.WHITE70,
            on_click=lambda e: self._on_search_submit(None),
        )
        
        self._favorites_button = ft.IconButton(
            icon=ft.Icons.FAVORITE_BORDER_ROUNDED,
            icon_color=ft.Colors.WHITE38,
            selected_icon=ft.Icons.FAVORITE_ROUNDED,
            selected_icon_color=ft.Colors.PINK_400,
            selected=False,
            tooltip="Show favorites only",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                bgcolor={"": "#1a1a2e"},
            ),
            on_click=self._toggle_favorites_filter,
        )
        
        # Content type tabs
        self._content_tabs = ft.Row(
            scroll=ft.ScrollMode.AUTO,
            spacing=6,
        )
        self._update_content_tabs()
        
        self._group_chips = ft.Row(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )
        
        self._channel_list = ft.ListView(
            spacing=4,
            padding=ft.padding.only(top=8, bottom=8),
            expand=True,
            auto_scroll=False,
        )
        
        # Load more button
        self._load_more_btn = ft.Container(
            content=ft.ElevatedButton(
                text="Load More",
                icon=ft.Icons.EXPAND_MORE_ROUNDED,
                bgcolor=ft.Colors.PURPLE_700,
                color=ft.Colors.WHITE,
                on_click=self._load_more,
            ),
            alignment=ft.alignment.center,
            padding=ft.padding.symmetric(vertical=12),
            visible=False,
        )
        
        # Channel count - create BEFORE _apply_filters
        self._channel_count = ft.Text(
            f"{len(self._channels)} total",
            size=12,
            color=ft.Colors.WHITE38,
        )
        
        self._displayed_info = ft.Text(
            "",
            size=11,
            color=ft.Colors.PURPLE_300,
        )
        
        self._update_group_chips()
        # Initial filter - don't call _apply_filters here, just set up data
        self._filtered_channels = self._channels.copy()
        self._load_initial_page()
        
        self.content = ft.Column(
            [
                # Header
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(
                                "Library",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Column(
                                [self._channel_count, self._displayed_info],
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.padding.only(bottom=12),
                ),
                # Content type tabs
                self._content_tabs,
                ft.Container(height=12),
                # Search bar row
                ft.Row(
                    [
                        ft.Container(
                            content=self._search_field,
                            expand=True,
                        ),
                        self._search_btn,
                        self._favorites_button,
                    ],
                    spacing=8,
                ),
                # Group chips
                ft.Container(
                    content=self._group_chips,
                    padding=ft.padding.symmetric(vertical=12),
                ),
                # Divider
                ft.Container(
                    height=1,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                ),
                # Channel list with lazy loading
                ft.Container(
                    content=ft.Column(
                        [
                            self._channel_list,
                            self._load_more_btn,
                        ],
                        spacing=0,
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        self.padding = ft.padding.all(20)
        self.expand = True
    
    def _load_initial_page(self):
        """Load initial page without triggering updates."""
        self._displayed_count = 0
        end = min(self.PAGE_SIZE, len(self._filtered_channels))
        for i in range(end):
            self._channel_list.controls.append(
                self._build_channel_tile(self._filtered_channels[i])
            )
        self._displayed_count = end
        
        total = len(self._filtered_channels)
        if self._displayed_count < total:
            self._displayed_info.value = f"Showing {self._displayed_count} of {total}"
            self._load_more_btn.visible = True
    
    def _update_content_tabs(self):
        """Update content type tabs."""
        self._content_tabs.controls = [
            self._create_content_tab("all", "All", ft.Icons.APPS_ROUNDED),
            self._create_content_tab("live", "Live TV", ft.Icons.LIVE_TV_ROUNDED),
            self._create_content_tab("movies", "Movies", ft.Icons.MOVIE_ROUNDED),
            self._create_content_tab("series", "Series", ft.Icons.TV_ROUNDED),
        ]
    
    def _create_content_tab(self, tab_id: str, label: str, icon) -> ft.Control:
        """Create a content type tab."""
        is_selected = self._content_type == tab_id
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE54),
                    ft.Text(label, size=12, color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE54),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=20,
            bgcolor=ft.Colors.PURPLE_700 if is_selected else "#1a1a2e",
            on_click=lambda e, t=tab_id: self._select_content_type(t),
        )
    
    def _select_content_type(self, content_type: str):
        """Select content type filter."""
        if self._is_updating:
            return
        self._content_type = content_type
        self._selected_group = None
        self._search_query = ""
        self._search_field.value = ""
        self._update_content_tabs()
        self._update_group_chips()
        self._apply_filters_safe()
    
    def _is_movie(self, channel: Channel) -> bool:
        """Check if channel is a movie."""
        group_lower = channel.group.lower()
        name_lower = channel.name.lower()
        movie_keywords = ['movie', 'film', 'cinema', 'vod', 'افلام', 'فيلم']
        return any(kw in group_lower or kw in name_lower for kw in movie_keywords)
    
    def _is_series(self, channel: Channel) -> bool:
        """Check if channel is a series/TV show."""
        group_lower = channel.group.lower()
        name_lower = channel.name.lower()
        series_keywords = ['series', 'serie', 'show', 'episode', 'season', 's0', 'e0', 'مسلسل']
        return any(kw in group_lower or kw in name_lower for kw in series_keywords)
    
    def _is_live(self, channel: Channel) -> bool:
        """Check if channel is live TV."""
        return not self._is_movie(channel) and not self._is_series(channel)
    
    def _matches_content_type(self, channel: Channel) -> bool:
        """Check if channel matches current content type filter."""
        if self._content_type == "all":
            return True
        elif self._content_type == "live":
            return self._is_live(channel)
        elif self._content_type == "movies":
            return self._is_movie(channel)
        elif self._content_type == "series":
            return self._is_series(channel)
        return True
    
    def set_channels(self, channels: List[Channel], groups: List[str]):
        """Update the channel list."""
        self._channels = channels
        self._groups = groups
        self._channel_count.value = f"{len(channels)} total"
        self._update_group_chips()
        self._apply_filters_safe()
    
    def refresh(self):
        """Refresh the channel list display."""
        self._apply_filters_safe()
    
    def _update_group_chips(self):
        """Update the group filter chips."""
        chips = []
        
        # Get groups for current content type
        if self._content_type != "all":
            visible_channels = [ch for ch in self._channels if self._matches_content_type(ch)]
            filtered_groups = list(set(ch.group for ch in visible_channels))
            filtered_groups.sort()
        else:
            filtered_groups = self._groups
        
        # All chip
        all_selected = self._selected_group is None
        chips.append(
            ft.Container(
                content=ft.Text("All", size=13, color=ft.Colors.WHITE if all_selected else ft.Colors.WHITE70),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                border_radius=20,
                bgcolor=ft.Colors.PURPLE_700 if all_selected else "#1a1a2e",
                on_click=lambda e: self._select_group(None),
            )
        )
        
        # Limit to prevent UI lag
        for group in filtered_groups[:15]:
            is_selected = self._selected_group == group
            display_name = group[:16] + "..." if len(group) > 16 else group
            chips.append(
                ft.Container(
                    content=ft.Text(
                        display_name,
                        size=13,
                        color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE70,
                    ),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    border_radius=20,
                    bgcolor=ft.Colors.PURPLE_700 if is_selected else "#1a1a2e",
                    on_click=lambda e, g=group: self._select_group(g),
                )
            )
        
        if len(filtered_groups) > 15:
            chips.append(
                ft.Container(
                    content=ft.Text(
                        f"+{len(filtered_groups) - 15} more",
                        size=12,
                        color=ft.Colors.WHITE38,
                    ),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                )
            )
        
        self._group_chips.controls = chips
    
    def _apply_filters_safe(self):
        """Apply filters with safe update mechanism."""
        if self._is_updating:
            return
        
        self._is_updating = True
        
        try:
            self._filtered_channels = self._channels.copy()
            
            # Filter by content type
            if self._content_type != "all":
                self._filtered_channels = [
                    ch for ch in self._filtered_channels 
                    if self._matches_content_type(ch)
                ]
            
            # Filter by favorites
            if self._show_favorites_only:
                self._filtered_channels = [
                    ch for ch in self._filtered_channels if ch.is_favorite
                ]
            
            # Filter by group
            if self._selected_group:
                self._filtered_channels = [
                    ch for ch in self._filtered_channels 
                    if ch.group == self._selected_group
                ]
            
            # Filter by search query
            if self._search_query:
                query = self._search_query.lower()
                self._filtered_channels = [
                    ch for ch in self._filtered_channels
                    if query in ch.name.lower() or query in ch.group.lower()
                ]
            
            # Rebuild channel list
            self._displayed_count = 0
            self._channel_list.controls.clear()
            
            # Load first page
            end = min(self.PAGE_SIZE, len(self._filtered_channels))
            for i in range(end):
                self._channel_list.controls.append(
                    self._build_channel_tile(self._filtered_channels[i])
                )
            self._displayed_count = end
            
            # Update info
            total = len(self._filtered_channels)
            self._channel_count.value = f"{total} items"
            
            if self._displayed_count < total:
                self._displayed_info.value = f"Showing {self._displayed_count} of {total}"
                self._load_more_btn.visible = True
            else:
                self._displayed_info.value = ""
                self._load_more_btn.visible = False
                
        finally:
            self._is_updating = False
        
        # Safe update
        if self.page:
            try:
                self.page.update()
            except Exception:
                pass
    
    def _load_more(self, e):
        """Load more channels."""
        if self._is_updating:
            return
            
        start = self._displayed_count
        end = min(start + self.PAGE_SIZE, len(self._filtered_channels))
        
        for i in range(start, end):
            self._channel_list.controls.append(
                self._build_channel_tile(self._filtered_channels[i])
            )
        
        self._displayed_count = end
        
        total = len(self._filtered_channels)
        if self._displayed_count < total:
            self._displayed_info.value = f"Showing {self._displayed_count} of {total}"
        else:
            self._displayed_info.value = ""
            self._load_more_btn.visible = False
        
        if self.page:
            try:
                self.page.update()
            except Exception:
                pass
    
    def _get_channel_icon(self, channel: Channel):
        """Get appropriate icon for channel type."""
        if self._is_movie(channel):
            return ft.Icons.MOVIE_ROUNDED
        elif self._is_series(channel):
            return ft.Icons.TV_ROUNDED
        else:
            return ft.Icons.LIVE_TV_ROUNDED
    
    def _build_channel_tile(self, channel: Channel) -> ft.Control:
        """Build a channel list tile - optimized for performance."""
        is_selected = self._selected_channel == channel
        
        # Simplified logo for performance
        if channel.logo:
            logo_content = ft.Image(
                src=channel.logo,
                width=32,
                height=32,
                fit=ft.ImageFit.CONTAIN,
                error_content=ft.Icon(
                    self._get_channel_icon(channel),
                    color=ft.Colors.WHITE54,
                    size=18,
                ),
            )
        else:
            logo_content = ft.Icon(
                self._get_channel_icon(channel),
                color=ft.Colors.WHITE54,
                size=18,
            )
        
        logo = ft.Container(
            content=logo_content,
            width=44,
            height=44,
            border_radius=10,
            bgcolor="#1a1a2e",
            alignment=ft.alignment.center,
        )
        
        # Clean display name
        display_name = channel.name[:45] + "..." if len(channel.name) > 45 else channel.name
        
        return ft.Container(
            content=ft.Row(
                [
                    logo,
                    ft.Container(width=10),
                    ft.Column(
                        [
                            ft.Text(
                                display_name,
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.WHITE,
                                max_lines=1,
                            ),
                            ft.Text(
                                channel.group[:30] if len(channel.group) <= 30 else channel.group[:27] + "...",
                                size=11,
                                color=ft.Colors.WHITE38,
                                max_lines=1,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.FAVORITE_ROUNDED if channel.is_favorite else ft.Icons.FAVORITE_BORDER_ROUNDED,
                        icon_color=ft.Colors.PINK_400 if channel.is_favorite else ft.Colors.WHITE24,
                        icon_size=18,
                        on_click=lambda e, ch=channel: self._toggle_favorite(ch),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=12,
            bgcolor="#1e1e32" if is_selected else "transparent",
            on_click=lambda e, ch=channel: self._select_channel(ch),
        )
    
    def _select_channel(self, channel: Channel):
        """Select a channel."""
        self._selected_channel = channel
        if self._on_channel_select:
            self._on_channel_select(channel)
    
    def _select_group(self, group: Optional[str]):
        """Select a group filter."""
        if self._is_updating:
            return
        self._selected_group = group
        self._update_group_chips()
        self._apply_filters_safe()
    
    def _toggle_favorite(self, channel: Channel):
        """Toggle favorite status of a channel."""
        if self._on_favorite_toggle:
            self._on_favorite_toggle(channel)
    
    def _toggle_favorites_filter(self, e):
        """Toggle favorites-only filter."""
        if self._is_updating:
            return
        self._show_favorites_only = not self._show_favorites_only
        self._favorites_button.selected = self._show_favorites_only
        self._apply_filters_safe()
    
    def _on_search_submit(self, e):
        """Handle search submission (on Enter or button click)."""
        if self._is_updating:
            return
        self._search_query = self._search_field.value or ""
        self._apply_filters_safe()
