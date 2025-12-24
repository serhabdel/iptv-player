"""Main application module."""
import flet as ft
from .views.hub_view import HubView
from .views.content_view import ContentView
from .views.series_view import SeriesView
from .views.player_view import PlayerView
from .views.settings_view import SettingsView
from .services.state_manager import StateManager
from .services.xtream_client import XtreamCodesClient, XtreamCredentials


class IPTVApp:
    """Main IPTV Player application with hub-based navigation."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.state = StateManager()
        self._current_view = "hub"
        self._current_content_type = "live"
        self._navigation_stack = []  # For back navigation
        
        self._setup_page()
        self._setup_views()
        self._show_hub()
        
        # Initial data load
        self.page.run_task(self._initial_load)
    
    def _setup_page(self):
        """Configure the page settings."""
        self.page.title = "IPTV Player"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0a0a0f"
        self.page.padding = 0
        self.page.spacing = 0
        
        # Window settings
        self.page.window.width = 1280
        self.page.window.height = 720
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        self.page.window.title_bar_hidden = False
        
        # Theme
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.PURPLE,
            font_family="Segoe UI",
        )
        
        # Keyboard handler for global shortcuts
        self.page.on_keyboard_event = self._on_keyboard
    
    def _setup_views(self): # Renamed from _build_views
        """Initialize all views."""
        self._hub_view = HubView(
            state_manager=self.state,
            on_hub_select=self._on_hub_select,
            on_settings_click=self._show_settings,
        )
        
        self._content_view = ContentView(
            state_manager=self.state,
            # content_type="live", # Removed content_type here as it's set dynamically
            on_channel_select=self._on_channel_select,
            on_back=self._go_back,
            on_settings_click=self._show_settings,
        )
        
        self._player_view = PlayerView(
            state_manager=self.state,
            on_back=self._go_back,
            on_settings_click=self._show_settings,
        )
        
        self._settings_view = SettingsView(
            state_manager=self.state,
            on_back=self._go_back,
        )
        
        self._series_view = SeriesView(
            state_manager=self.state,
            on_back=self._go_back,
            on_play_episode=self._play_series_episode,
        )
        
        # Main container
        self._container = ft.Container(
            content=self._hub_view,
            expand=True,
        )
        
        self.page.add(self._container)
    
    def _show_hub(self):
        """Show the hub view."""
        self._navigation_stack = []  # Clear navigation stack
        self._current_view = "hub"
        self._hub_view.refresh()
        self._container.content = self._hub_view
        self.page.update()
    
    def _show_content(self, content_type: str):
        """Show content view for a specific type."""
        self._navigation_stack.append(self._current_view)
        self._current_view = "content"
        self._current_content_type = content_type
        self._content_view.set_content_type(content_type)
        self._container.content = self._content_view
        self.page.update()
    
    def _show_player(self):
        """Show the player view."""
        self._navigation_stack.append(self._current_view)
        self._current_view = "player"
        self._player_view.refresh()
        self._container.content = self._player_view
        self.page.update()
    
    def _show_settings(self):
        """Show settings view."""
        self._navigation_stack.append(self._current_view)
        self._current_view = "settings"
        self._container.content = self._settings_view
        self.page.update()
    
    def _go_back(self):
        """Navigate back."""
        if self._navigation_stack:
            previous = self._navigation_stack.pop()
            
            if previous == "hub":
                self._current_view = "hub"
                self._hub_view.refresh()
                self._container.content = self._hub_view
            elif previous == "content":
                self._current_view = "content"
                self._content_view.refresh()
                self._container.content = self._content_view
            elif previous == "player":
                self._current_view = "player"
                self._player_view.refresh()
                self._container.content = self._player_view
            elif previous == "series":
                self._current_view = "series"
                self._container.content = self._series_view
            else:
                # Default to hub
                self._current_view = "hub"
                self._hub_view.refresh()
                self._container.content = self._hub_view
        else:
            # No history, go to hub
            self._show_hub()
        
        self.page.update()
    
    def _on_hub_select(self, hub_id: str):
        """Handle hub selection."""
        if hub_id == "settings":
            self._show_settings()
        elif hub_id in ["live", "movie", "series"]:
            self._show_content(hub_id)
    
    def _show_series(self, series_name: str, episodes: list):
        """Show series detail view."""
        self._navigation_stack.append(self._current_view)
        self._current_view = "series"
        self._series_view.load_series(series_name, episodes)
        self._container.content = self._series_view
        self.page.update()
        
    def _play_series_episode(self, channel):
        """Play an episode from series view."""
        # Pass the episode list to player for next/prev navigation
        episodes = getattr(self._series_view, '_episodes', [])
        self._player_view.set_episode_context(episodes)
        
        self._show_player()
        self._player_view.play_channel(channel)
    
    def _on_channel_select(self, channel):
        """Handle channel selection."""
        # Check if it's a series
        if getattr(channel, 'content_type', '') == 'series':
            # Case 1: Xtream Series Wrapper (Lazy Load)
            if getattr(channel, 'url', '').startswith("xtream://series/"):
                 self.page.run_task(self._load_xtream_series, channel)
                 return
            
            # Case 2: Standard M3U/Cached Series (Pre-grouped)
            elif getattr(channel, 'series_name', ''):
                 episodes = self.state.get_series_episodes(channel.series_name)
                 if episodes:
                     self._show_series(channel.series_name, episodes)
                     return

        # Otherwise play directly
        # Clear episode context (not from series)
        self._player_view.set_episode_context([])
        self._show_player()
        self._player_view.play_channel(channel)

    async def _load_xtream_series(self, channel):
        """Lazy load episodes for an Xtream series."""
        # Show loading feedback (basic for now)
        self.page.splash = ft.ProgressBar()
        self.page.update()
        
        try:
            # Find playlist and metadata
            playlist = self.state.get_playlist_for_channel(channel)
            if not playlist:
                 print("Error: Playlist not found for channel")
                 raise Exception("Playlist not found")
            
            if not playlist.metadata:
                 print(f"Error: No metadata in playlist {playlist.name}")
                 # Try to recover validation info from source if possible?
                 # No, metadata MUST be there.
                 raise Exception("Missing credentials in playlist")

            print(f"Loading series episodes for {channel.series_name} (ID: {channel.series_id})")
            creds = XtreamCredentials.from_dict(playlist.metadata)
            client = XtreamCodesClient(creds)
            
            # Fetch details
            data = await client.get_series_info(channel.series_id)
            episodes_data = data.get("episodes", {})
            
            # Map to Channels
            episodes = []
            
            # Handle both list (rare) and dict (common) formats
            # Dict format: "1": [ep1, ep2], "2": [...] (Keys are season numbers)
            items_iter = episodes_data.values() if isinstance(episodes_data, dict) else episodes_data
            
            # Flatten if it's a dict of lists
            all_eps = []
            if isinstance(episodes_data, dict):
                for season_eps in episodes_data.values():
                    all_eps.extend(season_eps)
            else:
                all_eps = episodes_data

            from .models.channel import Channel
            for ep in all_eps:
                ep_id = str(ep.get("id", ""))
                ext = ep.get("container_extension", "mp4")
                url = client.build_series_episode_url(ep_id, ext)
                
                episodes.append(Channel(
                    name=ep.get("title", f"Episode {ep.get('episode_num')}"),
                    url=url,
                    logo=ep.get("info", {}).get("movie_image", "") or channel.logo, # Fallback to series logo
                    group=channel.group,
                    content_type="series",
                    series_name=channel.name,
                    season=int(ep.get("season", 1)),
                    episode=int(ep.get("episode_num", 0)),
                ))
            
            self.page.splash = None
            self.page.update()
            
            self._show_series(channel.name, episodes)
            
        except Exception as e:
            self.page.splash = None
            print(f"Error loading series: {e}")
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Error loading series: {e}"))
            self.page.snack_bar.open = True
            self.page.update()
    
    def _on_keyboard(self, e: ft.KeyboardEvent):
        """Handle global keyboard events."""
        if e.key == "Escape" or e.key == "Backspace":
            self._go_back()
        elif e.key == "H" and e.ctrl:
            # Ctrl+H: Go to hub
            self._show_hub()
    
    async def _initial_load(self):
        """Initial load after UI is ready."""
        import asyncio
        await asyncio.sleep(0.2)
        
        # Refresh content counts
        
        # Refresh hub view with updated counts
        self._hub_view.refresh()
        self.page.update()


def main(page: ft.Page):
    """Application entry point."""
    IPTVApp(page)
