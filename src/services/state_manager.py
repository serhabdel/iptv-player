"""State management service for the IPTV player."""
import json
from pathlib import Path
from typing import List, Optional, Set, Callable, TYPE_CHECKING
from ..models.channel import Channel
from ..models.playlist import Playlist

if TYPE_CHECKING:
    from .xtream_client import XtreamCredentials


class StateManager:
    """Manages application state and persistence."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize state manager."""
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path.home() / ".iptv-player"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._favorites_file = self.data_dir / "favorites.json"
        self._playlists_file = self.data_dir / "playlists.json"
        self._settings_file = self.data_dir / "settings.json"
        self._xtream_file = self.data_dir / "xtream.json"
        self._channels_cache_dir = self.data_dir / "cache"
        self._channels_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory state
        self._playlists: List[Playlist] = []
        self._favorites: Set[str] = set()  # Set of channel URLs
        self._current_channel: Optional[Channel] = None
        self._settings: dict = {}
        self._xtream_providers: List[dict] = []  # List of Xtream Codes credentials
        
        # Callbacks
        self._on_playlist_change: List[Callable] = []
        self._on_favorites_change: List[Callable] = []
        self._on_channel_change: List[Callable] = []
        
        # Load persisted data
        self._load_data()
    
    def _load_data(self):
        """Load persisted data from files."""
        # Load favorites
        if self._favorites_file.exists():
            try:
                data = json.loads(self._favorites_file.read_text())
                self._favorites = set(data.get("favorites", []))
            except Exception:
                self._favorites = set()
        
        # Load settings
        if self._settings_file.exists():
            try:
                self._settings = json.loads(self._settings_file.read_text())
            except Exception:
                self._settings = {}
        
        # Load cached playlists
        if self._playlists_file.exists():
            try:
                data = json.loads(self._playlists_file.read_text())
                for p_data in data.get("playlists", []):
                    playlist = self._load_playlist_from_cache(p_data)
                    if playlist:
                        self._playlists.append(playlist)
            except Exception:
                pass
        
        # Load Xtream Codes providers
        self._load_xtream_providers()
    
    def _load_playlist_from_cache(self, p_data: dict) -> Optional[Playlist]:
        """Load a playlist from cache."""
        try:
            name = p_data.get("name", "Playlist")
            source = p_data.get("source", "")
            cache_file = p_data.get("cache_file", "")
            
            if cache_file:
                cache_path = self._channels_cache_dir / cache_file
                if cache_path.exists():
                    channels_data = json.loads(cache_path.read_text())
                    channels = []
                    for ch_data in channels_data:
                        channel = Channel(
                            name=ch_data.get("name", "Unknown"),
                            url=ch_data.get("url", ""),
                            logo=ch_data.get("logo", ""),
                            group=ch_data.get("group", "Uncategorized"),
                            is_favorite=ch_data.get("url", "") in self._favorites
                        )
                        channels.append(channel)
                    
                    return Playlist(name=name, source=source, channels=channels)
            
            return None
        except Exception:
            return None
    
    def _save_favorites(self):
        """Save favorites to file."""
        data = {"favorites": list(self._favorites)}
        self._favorites_file.write_text(json.dumps(data, indent=2))
    
    def _save_playlists(self):
        """Save playlists to file with channel caching."""
        playlists_data = []
        
        for i, playlist in enumerate(self._playlists):
            # Save channels to cache file
            cache_file = f"playlist_{i}.json"
            cache_path = self._channels_cache_dir / cache_file
            
            channels_data = [
                {
                    "name": ch.name,
                    "url": ch.url,
                    "logo": ch.logo,
                    "group": ch.group,
                }
                for ch in playlist.channels
            ]
            cache_path.write_text(json.dumps(channels_data))
            
            playlists_data.append({
                "name": playlist.name,
                "source": playlist.source,
                "cache_file": cache_file,
            })
        
        data = {"playlists": playlists_data}
        self._playlists_file.write_text(json.dumps(data, indent=2))
    
    def _save_settings(self):
        """Save settings to file."""
        self._settings_file.write_text(json.dumps(self._settings, indent=2))
    
    # Playlist management
    def add_playlist(self, playlist: Playlist):
        """Add a playlist to the state."""
        # Apply favorites to channels
        for channel in playlist.channels:
            if channel.url in self._favorites:
                channel.is_favorite = True
        
        self._playlists.append(playlist)
        self._save_playlists()
        self._notify_playlist_change()
    
    def remove_playlist(self, playlist: Playlist):
        """Remove a playlist from the state."""
        if playlist in self._playlists:
            self._playlists.remove(playlist)
            self._save_playlists()
            self._notify_playlist_change()
    
    def get_playlists(self) -> List[Playlist]:
        """Get all playlists."""
        return self._playlists
    
    def get_all_channels(self, playlist_filter: Optional[str] = None) -> List[Channel]:
        """Get all channels, optionally filtered by playlist name."""
        channels = []
        for playlist in self._playlists:
            if playlist_filter is None or playlist_filter == "All Playlists" or playlist.name == playlist_filter:
                channels.extend(playlist.channels)
        return channels
    
    def get_all_groups(self, playlist_filter: Optional[str] = None) -> List[str]:
        """Get all unique groups, optionally filtered by playlist name."""
        groups = set()
        for playlist in self._playlists:
            if playlist_filter is None or playlist_filter == "All Playlists" or playlist.name == playlist_filter:
                groups.update(playlist.get_groups())
        return sorted(list(groups))
    
    def get_channels_by_group(self, group: str, playlist_filter: Optional[str] = None) -> List[Channel]:
        """Get all channels in a group, optionally filtered by playlist."""
        channels = []
        for playlist in self._playlists:
            if playlist_filter is None or playlist_filter == "All Playlists" or playlist.name == playlist_filter:
                channels.extend(playlist.get_channels_by_group(group))
        return channels
    
    def search_channels(self, query: str) -> List[Channel]:
        """Search channels across all playlists."""
        channels = []
        for playlist in self._playlists:
            channels.extend(playlist.search_channels(query))
        return channels
    
    # Favorites management
    def toggle_favorite(self, channel: Channel) -> bool:
        """Toggle favorite status of a channel."""
        if channel.url in self._favorites:
            self._favorites.discard(channel.url)
            channel.is_favorite = False
        else:
            self._favorites.add(channel.url)
            channel.is_favorite = True
        
        self._save_favorites()
        self._notify_favorites_change()
        return channel.is_favorite
    
    def get_favorites(self) -> List[Channel]:
        """Get all favorite channels."""
        favorites = []
        for playlist in self._playlists:
            favorites.extend(playlist.get_favorites())
        return favorites
    
    def is_favorite(self, channel: Channel) -> bool:
        """Check if a channel is a favorite."""
        return channel.url in self._favorites
    
    # Current channel
    def set_current_channel(self, channel: Optional[Channel]):
        """Set the currently playing channel."""
        self._current_channel = channel
        self._notify_channel_change()
    
    def get_current_channel(self) -> Optional[Channel]:
        """Get the currently playing channel."""
        return self._current_channel
    
    # Settings
    def get_setting(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)
    
    def set_setting(self, key: str, value):
        """Set a setting value."""
        self._settings[key] = value
        self._save_settings()
    
    # Callbacks
    def on_playlist_change(self, callback: Callable):
        """Register callback for playlist changes."""
        self._on_playlist_change.append(callback)
    
    def on_favorites_change(self, callback: Callable):
        """Register callback for favorites changes."""
        self._on_favorites_change.append(callback)
    
    def on_channel_change(self, callback: Callable):
        """Register callback for current channel changes."""
        self._on_channel_change.append(callback)
    
    def _notify_playlist_change(self):
        """Notify all playlist change callbacks."""
        for callback in self._on_playlist_change:
            callback()
    
    def _notify_favorites_change(self):
        """Notify all favorites change callbacks."""
        for callback in self._on_favorites_change:
            callback()
    
    def _notify_channel_change(self):
        """Notify all channel change callbacks."""
        for callback in self._on_channel_change:
            callback()
    
    # Xtream Codes Provider Management
    def _load_xtream_providers(self):
        """Load Xtream Codes providers from file."""
        if self._xtream_file.exists():
            try:
                data = json.loads(self._xtream_file.read_text())
                self._xtream_providers = data.get("providers", [])
            except Exception:
                self._xtream_providers = []
    
    def _save_xtream_providers(self):
        """Save Xtream Codes providers to file."""
        data = {"providers": self._xtream_providers}
        self._xtream_file.write_text(json.dumps(data, indent=2))
    
    def add_xtream_provider(self, credentials: "XtreamCredentials"):
        """Add an Xtream Codes provider."""
        # Check if provider already exists (by server+username)
        for provider in self._xtream_providers:
            if provider.get("server") == credentials.server and provider.get("username") == credentials.username:
                # Update existing
                provider.update(credentials.to_dict())
                self._save_xtream_providers()
                return
        
        self._xtream_providers.append(credentials.to_dict())
        self._save_xtream_providers()
        self._notify_playlist_change()
    
    def remove_xtream_provider(self, server: str, username: str):
        """Remove an Xtream Codes provider."""
        self._xtream_providers = [
            p for p in self._xtream_providers
            if not (p.get("server") == server and p.get("username") == username)
        ]
        self._save_xtream_providers()
        self._notify_playlist_change()
    
    def get_xtream_providers(self) -> List[dict]:
        """Get all Xtream Codes providers."""
        return self._xtream_providers.copy()
