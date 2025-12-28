"""Content view with categories sidebar and grid/list display."""
import flet as ft
import asyncio
from typing import Optional, Callable, List
from ..models.channel import Channel
from ..services.state_manager import StateManager
from ..components.skeleton_loader import SkeletonGrid, SkeletonList


class ContentView(ft.Container):
    """Content view with categories sidebar and content grid."""
    
    def __init__(
        self,
        state_manager: StateManager,
        content_type: str = "live",  # live, movie, series
        on_channel_select: Optional[Callable[[Channel], None]] = None,
        on_back: Optional[Callable] = None,
        on_settings_click: Optional[Callable] = None,
    ):
        super().__init__()
        self.state = state_manager
        self.content_type = content_type
        self._on_channel_select = on_channel_select
        self._on_back = on_back
        self._on_settings_click = on_settings_click
        
        # State
        self._selected_category = "All"
        self._search_query = ""
        self._channels: List[Channel] = []
        self._displayed_channels: List[Channel] = []
        self._page_size = 50
        self._current_page = 0
        
        # Loading state
        self._is_loading = True
        
        # Skeleton loaders
        self._skeleton_grid = SkeletonGrid(items_per_row=5, rows=3)
        self._skeleton_list = SkeletonList(items=12)
        
        # UI components - Using ListView for virtualized rendering
        self._category_list = ft.ListView(spacing=4, expand=True)
        self._content_grid = ft.ListView(
            spacing=8,
            item_extent=220,  # Fixed height for grid rows (improves scroll perf)
            expand=True,
        )
        self._search_field = None
        self._channel_count_text = None
        
        self._build_ui()
    
    def _get_title(self) -> str:
        """Get the title for the current content type."""
        titles = {
            "live": "Live TV",
            "movie": "Movies",
            "series": "TV Series",
        }
        return titles.get(self.content_type, "Content")
    
    def _get_icon(self) -> str:
        """Get the icon for the current content type."""
        icons = {
            "live": ft.Icons.LIVE_TV_ROUNDED,
            "movie": ft.Icons.MOVIE_ROUNDED,
            "series": ft.Icons.TV_ROUNDED,
        }
        return icons.get(self.content_type, ft.Icons.VIDEO_LIBRARY_ROUNDED)
    
    def _build_ui(self):
        """Build the content view UI."""
        # Load channels for this content type
        self._load_channels()
        
        # Header
        header = self._build_header()
        
        # Categories sidebar
        categories_sidebar = self._build_categories_sidebar()
        
        # Main content area
        content_area = self._build_content_area()
        
        # Layout
        main_row = ft.Row(
            [
                categories_sidebar,
                ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
                content_area,
            ],
            expand=True,
            spacing=0,
        )
        
        self.content = ft.Column(
            [
                header,
                main_row,
            ],
            expand=True,
            spacing=0,
        )
        self.expand = True
        self.bgcolor = "#0a0a12"
    
    def _build_header(self) -> ft.Container:
        """Build the header with back button and title."""
        self._search_field = ft.TextField(
            hint_text=f"Search {self._get_title().lower()}...",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            border_radius=8,
            bgcolor="#2a2a3e",
            border_color="transparent",
            focused_border_color="#6366f1",
            color=ft.Colors.WHITE,
            hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
            height=40,
            width=300,
            on_change=self._on_search_change,
        )
        
        return ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                icon_size=24,
                                tooltip="Back",
                                on_click=lambda e: self._on_back() if self._on_back else None,
                            ),
                            ft.Icon(self._get_icon(), color=ft.Colors.WHITE, size=24),
                            ft.Text(
                                self._get_title(),
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        [
                            self._search_field,
                            ft.IconButton(
                                icon=ft.Icons.SETTINGS_ROUNDED,
                                icon_color=ft.Colors.WHITE70,
                                tooltip="Settings",
                                on_click=lambda e: self._on_settings_click() if self._on_settings_click else None,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor="#1a1a2e",
        )
    
    def _build_categories_sidebar(self) -> ft.Container:
        """Build the categories sidebar."""
        # Get unique categories/groups
        categories = self._get_categories()
        
        # Build category buttons
        self._category_list.controls.clear()
        
        # All category
        self._category_list.controls.append(
            self._create_category_button("All", len(self._channels))
        )
        
        # Individual categories
        for category, count in categories[:50]:  # Limit to 50 categories
            self._category_list.controls.append(
                self._create_category_button(category, count)
            )
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Categories",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.WHITE70,
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=self._category_list,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            width=220,
            padding=ft.padding.all(16),
            bgcolor="#0f0f1a",
        )
    
    def _create_category_button(self, name: str, count: int) -> ft.Container:
        """Create a category button."""
        is_selected = name == self._selected_category
        
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        name if len(name) <= 20 else name[:18] + "...",
                        size=13,
                        color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE70,
                        weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Text(
                            f"{count:,}" if count < 10000 else f"{count//1000}k",
                            size=11,
                            color=ft.Colors.WHITE54,
                        ),
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4,
                        bgcolor=ft.Colors.WHITE10 if is_selected else None,
                    ),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor="#6366f1" if is_selected else None,
            on_click=lambda e, cat=name: self._on_category_select(cat),
            on_hover=lambda e: self._on_category_hover(e),
        )
    
    def _on_category_hover(self, e):
        """Handle category hover."""
        if e.data == "true":
            e.control.bgcolor = e.control.bgcolor or ft.Colors.WHITE10
        else:
            if self._selected_category != e.control.content.controls[0].value[:20]:
                e.control.bgcolor = None
        if self.page:
            e.control.update()
    
    def _build_content_area(self) -> ft.Container:
        """Build the main content area with grid."""
        self._channel_count_text = ft.Text(
            f"{len(self._displayed_channels):,} items",
            size=12,
            color=ft.Colors.WHITE54,
        )
        
        # Build content grid
        self._update_content_grid()
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            self._channel_count_text,
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.GRID_VIEW_ROUNDED,
                                        icon_color=ft.Colors.WHITE70,
                                        icon_size=20,
                                        tooltip="Grid view",
                                        selected=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.LIST_ROUNDED,
                                        icon_color=ft.Colors.WHITE38,
                                        icon_size=20,
                                        tooltip="List view",
                                    ),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=self._content_grid,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            expand=True,
            padding=ft.padding.all(16),
        )
    
    def _update_content_grid(self):
        """Update the content grid with current channels."""
        self._content_grid.controls.clear()
        
        # Show skeleton during loading
        if self._is_loading:
            if self.content_type in ["movie", "series"]:
                self._content_grid.controls.append(self._skeleton_grid)
            else:
                self._content_grid.controls.append(self._skeleton_list)
            return
        
        # Filter channels
        channels = self._get_filtered_channels()
        self._displayed_channels = channels
        
        if self._channel_count_text:
            self._channel_count_text.value = f"{len(channels):,} items"
        
        if not channels:
            self._content_grid.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=64, color=ft.Colors.WHITE24),
                            ft.Text(
                                "No content found",
                                size=16,
                                color=ft.Colors.WHITE54,
                            ),
                            ft.Text(
                                "Try selecting a different category or search term",
                                size=13,
                                color=ft.Colors.WHITE38,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    expand=True,
                    alignment=ft.alignment.center,
                )
            )
            return
        
        # Create grid rows (4 items per row for movies/series, list for live)
        if self.content_type in ["movie", "series"]:
            self._build_grid_view(channels)
        else:
            self._build_list_view(channels)
    
    def _build_grid_view(self, channels: List[Channel]):
        """Build grid view for movies/series."""
        items_per_row = 5
        displayed = channels[:self._page_size]
        
        for i in range(0, len(displayed), items_per_row):
            row_items = displayed[i:i + items_per_row]
            row = ft.Row(
                [self._create_grid_card(ch) for ch in row_items],
                spacing=12,
                wrap=True,
            )
            self._content_grid.controls.append(row)
        
        # Load more button
        if len(channels) > self._page_size:
            self._content_grid.controls.append(
                ft.Container(
                    content=ft.ElevatedButton(
                        text=f"Load More ({len(channels) - self._page_size:,} remaining)",
                        icon=ft.Icons.EXPAND_MORE_ROUNDED,
                        bgcolor="#6366f1",
                        color=ft.Colors.WHITE,
                        on_click=self._load_more,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=16),
                )
            )
    
    def _build_list_view(self, channels: List[Channel]):
        """Build list view for live TV."""
        displayed = channels[:self._page_size]
        
        for channel in displayed:
            self._content_grid.controls.append(self._create_list_item(channel))
        
        # Load more button
        if len(channels) > self._page_size:
            self._content_grid.controls.append(
                ft.Container(
                    content=ft.ElevatedButton(
                        text=f"Load More ({len(channels) - self._page_size:,} remaining)",
                        icon=ft.Icons.EXPAND_MORE_ROUNDED,
                        bgcolor="#6366f1",
                        color=ft.Colors.WHITE,
                        on_click=self._load_more,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=16),
                )
            )
    
    def _create_grid_card(self, channel: Channel) -> ft.Container:
        """Create a grid card for movie/series with favorite overlay."""
        # Favorite button overlay
        fav_overlay = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.FAVORITE_ROUNDED if channel.is_favorite else ft.Icons.FAVORITE_BORDER_ROUNDED,
                icon_color=ft.Colors.PINK_400 if channel.is_favorite else ft.Colors.WHITE70,
                icon_size=18,
                on_click=lambda e, ch=channel: self._handle_favorite_toggle(ch),
                style=ft.ButtonStyle(padding=4),
            ),
            right=4,
            top=4,
            bgcolor="#00000080",
            border_radius=20,
        )
        
        # Poster with overlay
        poster_stack = ft.Stack(
            [
                # Poster/Logo
                ft.Container(
                    content=ft.Image(
                        src=channel.logo,
                        width=140,
                        height=200,
                        fit=ft.ImageFit.COVER,
                        error_content=ft.Container(
                            content=ft.Icon(
                                ft.Icons.MOVIE_ROUNDED if self.content_type == "movie" else ft.Icons.TV_ROUNDED,
                                size=48,
                                color=ft.Colors.WHITE24,
                            ),
                            alignment=ft.alignment.center,
                        ),
                    ) if channel.logo else ft.Container(
                        content=ft.Icon(
                            ft.Icons.MOVIE_ROUNDED if self.content_type == "movie" else ft.Icons.TV_ROUNDED,
                            size=48,
                            color=ft.Colors.WHITE24,
                        ),
                        alignment=ft.alignment.center,
                    ),
                    width=140,
                    height=200,
                    border_radius=8,
                    bgcolor="#1a1a2e",
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                fav_overlay,
            ],
            width=140,
            height=200,
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    poster_stack,
                    # Title
                    ft.Container(
                        content=ft.Text(
                            channel.name,
                            size=12,
                            color=ft.Colors.WHITE,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        width=140,
                        padding=ft.padding.only(top=8),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            on_click=lambda e, ch=channel: self._handle_channel_select(ch),
            border_radius=8,
            padding=ft.padding.all(8),
            ink=True,
            on_hover=lambda e: self._on_card_hover(e),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
    
    def _create_list_item(self, channel: Channel) -> ft.Container:
        """Create a list item for live TV."""
        return ft.Container(
            content=ft.Row(
                [
                    # Logo
                    ft.Container(
                        content=ft.Image(
                            src=channel.logo,
                            width=60,
                            height=40,
                            fit=ft.ImageFit.CONTAIN,
                        ) if channel.logo else ft.Icon(
                            ft.Icons.LIVE_TV_ROUNDED,
                            size=24,
                            color=ft.Colors.WHITE38,
                        ),
                        width=60,
                        height=40,
                        alignment=ft.alignment.center,
                    ),
                    # Info
                    ft.Column(
                        [
                            ft.Text(
                                channel.name,
                                size=14,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.W_500,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                channel.group,
                                size=12,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    # Favorite
                    ft.IconButton(
                        icon=ft.Icons.FAVORITE_ROUNDED if channel.is_favorite else ft.Icons.FAVORITE_BORDER_ROUNDED,
                        icon_color=ft.Colors.PINK_400 if channel.is_favorite else ft.Colors.WHITE38,
                        icon_size=20,
                        on_click=lambda e, ch=channel: self._handle_favorite_toggle(ch),
                    ),
                ],
                spacing=16,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=8,
            bgcolor="#1a1a2e",
            on_click=lambda e, ch=channel: self._handle_channel_select(ch),
            on_hover=lambda e: self._on_item_hover(e),
        )
    
    def _on_card_hover(self, e):
        """Handle card hover with focus indicator for D-pad navigation."""
        if e.data == "true":
            e.control.bgcolor = ft.Colors.WHITE10
            e.control.border = ft.border.all(2, ft.Colors.PURPLE_400)
            e.control.scale = 1.03
        else:
            e.control.bgcolor = None
            e.control.border = None
            e.control.scale = 1.0
        if self.page:
            e.control.update()
    
    def _on_item_hover(self, e):
        """Handle list item hover with focus indicator."""
        if e.data == "true":
            e.control.bgcolor = "#252538"
            e.control.border = ft.border.all(2, ft.Colors.PURPLE_400)
        else:
            e.control.bgcolor = "#1a1a2e"
            e.control.border = None
        if self.page:
            e.control.update()
    
    def _load_channels(self):
        """Load channels for current content type."""
        self._channels = self.state.get_channels_by_type(self.content_type)
        self._displayed_channels = self._channels
        self._is_loading = False  # Mark loading complete
    def _get_categories(self) -> List[tuple]:
        """Get unique categories with counts."""
        category_counts = {}
        for ch in self._channels:
            group = ch.group or "Uncategorized"
            category_counts[group] = category_counts.get(group, 0) + 1
        
        # Sort by count descending
        return sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    def _get_filtered_channels(self) -> List[Channel]:
        """Get channels filtered by category and search."""
        channels = self._channels
        
        # Filter by category
        if self._selected_category != "All":
            channels = [ch for ch in channels if ch.group == self._selected_category]
        
        # Filter by search
        if self._search_query:
            query = self._search_query.lower()
            channels = [ch for ch in channels if query in ch.name.lower()]
        
        return channels
    
    def _on_category_select(self, category: str):
        """Handle category selection."""
        self._selected_category = category
        self._page_size = 50
        
        # Rebuild categories to update selection
        categories = self._get_categories()
        self._category_list.controls.clear()
        self._category_list.controls.append(
            self._create_category_button("All", len(self._channels))
        )
        for cat, count in categories[:50]:
            self._category_list.controls.append(
                self._create_category_button(cat, count)
            )
        
        # Update content
        self._update_content_grid()
        
        if self.page:
            self.page.update()
    
    def _on_search_change(self, e):
        """Handle search input change."""
        self._search_query = e.control.value
        self._page_size = 50
        self._update_content_grid()
        if self.page:
            self.page.update()
    
    def _load_more(self, e):
        """Load more items."""
        self._page_size += 50
        self._update_content_grid()
        if self.page:
            self.page.update()
    
    def _handle_channel_select(self, channel: Channel):
        """Handle channel selection."""
        self.state.add_to_recently_viewed(channel)
        if self._on_channel_select:
            self._on_channel_select(channel)
    
    def _handle_favorite_toggle(self, channel: Channel):
        """Handle favorite toggle."""
        self.state.toggle_favorite(channel)
        self._update_content_grid()
        if self.page:
            self.page.update()
    
    def set_content_type(self, content_type: str):
        """Change the content type with loading transition."""
        self.content_type = content_type
        self._selected_category = "All"
        self._search_query = ""
        self._page_size = 50
        self._is_loading = True  # Show skeleton
        self._build_ui()
        if self.page:
            self.update()
            # Trigger async load for smooth transition
            self.page.run_task(self._async_load_content)
    
    async def _async_load_content(self):
        """Async content loading with skeleton transition."""
        await asyncio.sleep(0.15)  # Brief delay for skeleton to show
        self._load_channels()
        self._update_content_grid()
        if self.page:
            self.page.update()
    
    def refresh(self):
        """Refresh the content view."""
        self._is_loading = True
        self._update_content_grid()
        if self.page:
            self.update()
            self.page.run_task(self._async_load_content)
