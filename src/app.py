"""Main application module."""
import flet as ft
from .views.player_view import PlayerView
from .views.settings_view import SettingsView
from .services.state_manager import StateManager


class IPTVApp:
    """Main IPTV Player application."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.state = StateManager()
        self._current_view = "player"
        
        self._setup_page()
        self._build_ui()
        
        # Playlists are now loaded from cache automatically
        # Just refresh the view to show them
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
    
    def _build_ui(self):
        """Build the main UI."""
        self._player_view = PlayerView(
            state_manager=self.state,
            on_settings_click=self._show_settings,
        )
        
        self._settings_view = SettingsView(
            state_manager=self.state,
            on_back=self._show_player,
        )
        
        self._container = ft.Container(
            content=self._player_view,
            expand=True,
        )
        
        self.page.add(self._container)
    
    def _show_settings(self):
        """Show settings view."""
        self._current_view = "settings"
        self._container.content = self._settings_view
        self.page.update()
    
    def _show_player(self):
        """Show player view."""
        self._current_view = "player"
        self._player_view.refresh()
        self._container.content = self._player_view
        self.page.update()
    
    async def _initial_load(self):
        """Initial load after UI is ready."""
        import asyncio
        await asyncio.sleep(0.2)  # Brief delay for UI to settle
        
        # Refresh player view with cached playlists
        if self.state.get_playlists():
            self._player_view.refresh()
            self.page.update()


def main(page: ft.Page):
    """Application entry point."""
    IPTVApp(page)
