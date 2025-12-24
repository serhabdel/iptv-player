"""State management service for the IPTV player."""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Set, Callable, Dict, TYPE_CHECKING
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
        self._recently_viewed_file = self.data_dir / "recently_viewed.json"
        self._epg_cache_file = self.data_dir / "epg_cache.json"
        self._channels_cache_dir = self.data_dir / "cache"
        self._channels_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory state
        self._playlists: List[Playlist] = []
        self._favorites: Set[str] = set()  # Set of channel URLs
        self._current_channel: Optional[Channel] = None
        self._settings: dict = {}
        self._xtream_providers: List[dict] = []  # List of Xtream Codes credentials
        self._recently_viewed: List[dict] = []  # List of {url, timestamp, name, logo, content_type}
        self._epg_data: Dict[str, List[dict]] = {}  # channel_id -> programs
        self._content_counts: Dict[str, int] = {"live": 0, "movie": 0, "series": 0}
        
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
        
        # Load recently viewed
        self._load_recently_viewed()
        
        # Load EPG cache
        self._load_epg_cache()
    
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
                        # Get content type (may be missing in old caches)
                        content_type = ch_data.get("content_type", None)
                        
                        # Auto-classify if missing
                        if not content_type:
                            content_type = self._detect_content_type(
                                ch_data.get("name", ""),
                                ch_data.get("group", ""),
                                ch_data.get("url", "")
                            )
                        
                        channel = Channel(
                            name=ch_data.get("name", "Unknown"),
                            url=ch_data.get("url", ""),
                            logo=ch_data.get("logo", ""),
                            group=ch_data.get("group", "Uncategorized"),
                            is_favorite=ch_data.get("url", "") in self._favorites,
                            content_type=content_type,
                            series_id=ch_data.get("series_id"),
                            series_name=ch_data.get("series_name"),
                            tvg_id=ch_data.get("tvg_id", ""),
                            epg_channel_id=ch_data.get("epg_channel_id", ""),
                            season=ch_data.get("season"),
                            episode=ch_data.get("episode"),
                        )
                        channels.append(channel)
                    
                    return Playlist(
                        name=name, 
                        source=source, 
                        channels=channels,
                        metadata=p_data.get("metadata", {})
                    )
            
            return None
        except Exception:
            return None
    
    def _detect_content_type(self, name: str, group: str, url: str) -> str:
        """Detect content type based on name, group, and URL patterns."""
        import re
        
        name_lower = name.lower()
        group_lower = group.lower()
        url_lower = url.lower()
        
        # Check URL patterns first (most reliable)
        if '/movie/' in url_lower or '/vod/' in url_lower:
            return 'movie'
        if '/series/' in url_lower or '/episode/' in url_lower:
            return 'series'
        if '/live/' in url_lower:
            return 'live'
        
        # Series patterns in name
        series_patterns = [
            r's\d{1,2}\s*e\d{1,2}', r'season\s*\d+', r'episode\s*\d+',
            r'ep\s*\d+', r'\bse?\d{1,2}\.?e?\d{1,2}\b', r'\[\d+x\d+\]',
        ]
        for pattern in series_patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return 'series'
        
        # Group patterns for series
        series_groups = ['series', 'tv show', 'show', 'episode', 'season', 'netflix', 'amazon', 'hbo']
        for pattern in series_groups:
            if pattern in group_lower:
                return 'series'
        
        # Group patterns for movies/VOD
        movie_groups = ['vod', 'movie', 'film', 'cinema', 'afflam', '4k movie', 'hd movie']
        for pattern in movie_groups:
            if pattern in group_lower:
                return 'movie'
        
        # Default to live
        return 'live'
    
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
                    "content_type": getattr(ch, 'content_type', 'live'),
                    "series_id": getattr(ch, 'series_id', None),
                    "series_name": getattr(ch, 'series_name', None),
                    "tvg_id": getattr(ch, 'tvg_id', ''),
                    "epg_channel_id": getattr(ch, 'epg_channel_id', ''),
                    "season": getattr(ch, 'season', None),
                    "episode": getattr(ch, 'episode', None),
                }
                for ch in playlist.channels
            ]
            cache_path.write_text(json.dumps(channels_data))
            
            # Metadata for playlist
            playlists_data.append({
                "name": playlist.name,
                "source": playlist.source,
                "cache_file": cache_file,
                "metadata": playlist.metadata,
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
    
    def clear_settings(self):
        """Clear all settings."""
        self._settings = {}
        self._save_settings()
    
    def clear_favorites(self):
        """Clear all favorites."""
        self._favorites.clear()
        # Update all channels to not be favorites
        for playlist in self._playlists:
            for channel in playlist.channels:
                channel.is_favorite = False
        self._save_favorites()
        self._notify_favorites_change()
    
    def clear_recently_viewed(self):
        """Clear recently viewed history."""
        self._recently_viewed.clear()
        self._save_recently_viewed()
    
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
    
    # Recently Viewed Management
    def _load_recently_viewed(self):
        """Load recently viewed from file."""
        if self._recently_viewed_file.exists():
            try:
                data = json.loads(self._recently_viewed_file.read_text())
                self._recently_viewed = data.get("recently_viewed", [])
            except Exception:
                self._recently_viewed = []
    
    def _save_recently_viewed(self):
        """Save recently viewed to file."""
        data = {"recently_viewed": self._recently_viewed}
        self._recently_viewed_file.write_text(json.dumps(data, indent=2))
    
    def add_to_recently_viewed(self, channel: Channel):
        """Add a channel to recently viewed list."""
        # Remove if already exists
        self._recently_viewed = [
            rv for rv in self._recently_viewed 
            if rv.get("url") != channel.url
        ]
        
        # Add to front of list
        self._recently_viewed.insert(0, {
            "url": channel.url,
            "name": channel.name,
            "logo": channel.logo,
            "group": channel.group,
            "content_type": channel.content_type,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 100 items
        self._recently_viewed = self._recently_viewed[:100]
        self._save_recently_viewed()
        
        # Update channel's last_watched
        channel.last_watched = datetime.now()
    
    def get_recently_viewed(self, limit: int = 50, content_type: Optional[str] = None) -> List[dict]:
        """Get recently viewed channels."""
        viewed = self._recently_viewed
        if content_type:
            viewed = [rv for rv in viewed if rv.get("content_type") == content_type]
        return viewed[:limit]
    
    def get_recently_viewed_channels(self, limit: int = 50, content_type: Optional[str] = None) -> List[Channel]:
        """Get recently viewed as Channel objects."""
        viewed = self.get_recently_viewed(limit, content_type)
        channels = []
        all_channels = {ch.url: ch for ch in self.get_all_channels()}
        
        for rv in viewed:
            url = rv.get("url")
            if url in all_channels:
                channels.append(all_channels[url])
        
        return channels
    
    # EPG Management
    def _load_epg_cache(self):
        """Load EPG data from cache."""
        if self._epg_cache_file.exists():
            try:
                data = json.loads(self._epg_cache_file.read_text())
                self._epg_data = data.get("epg", {})
            except Exception:
                self._epg_data = {}
    
    def _save_epg_cache(self):
        """Save EPG data to cache."""
        data = {"epg": self._epg_data}
        self._epg_cache_file.write_text(json.dumps(data))
    
    def set_epg_data(self, epg_data: Dict[str, List[dict]]):
        """Set EPG data for all channels."""
        self._epg_data = epg_data
        self._save_epg_cache()
    
    def get_epg_for_channel(self, channel_id: str) -> List[dict]:
        """Get EPG programs for a channel."""
        return self._epg_data.get(channel_id, [])
    
    def get_current_program(self, channel_id: str) -> Optional[dict]:
        """Get currently airing program for a channel."""
        programs = self.get_epg_for_channel(channel_id)
        now = datetime.now()
        
        for program in programs:
            try:
                start = datetime.fromisoformat(program.get("start", ""))
                end = datetime.fromisoformat(program.get("end", ""))
                if start <= now <= end:
                    return program
            except (ValueError, TypeError):
                continue
        return None
    
    def get_next_program(self, channel_id: str) -> Optional[dict]:
        """Get next program for a channel."""
        programs = self.get_epg_for_channel(channel_id)
        now = datetime.now()
        
        for program in programs:
            try:
                start = datetime.fromisoformat(program.get("start", ""))
                if start > now:
                    return program
            except (ValueError, TypeError):
                continue
        return None
    
    # Content Counts
    def get_content_counts(self) -> dict:
        """Get counts of channels by content type."""
        counts = {"live": 0, "movie": 0, "series": 0}
        
        for playlist in self._playlists:
            for channel in playlist.channels:
                c_type = getattr(channel, 'content_type', 'live')
                if c_type in counts:
                    counts[c_type] += 1
                else:
                    # Fallback for unknown types
                    counts["live"] += 1
                    
        return counts

    def get_series_episodes(self, series_name: str) -> list:
        """Get all episodes for a given series name."""
        episodes = []
        for playlist in self._playlists:
            for channel in playlist.channels:
                if getattr(channel, 'content_type', '') == 'series':
                    # Check exact match on series_name
                    if getattr(channel, 'series_name', '') == series_name:
                        episodes.append(channel)
        return episodes
    
    def get_playlist_for_channel(self, channel: Channel) -> Optional[Playlist]:
        """Find the playlist that contains a specific channel."""
        for playlist in self._playlists:
             if channel in playlist.channels:
                 return playlist
             # Fallback: check by URL
             for ch in playlist.channels:
                 if ch.url == channel.url:
                     return playlist
        return None

    def get_channels_by_type(self, content_type: str, playlist_filter: Optional[str] = None) -> List[Channel]:
        """Get all channels of a specific content type."""
        channels = self.get_all_channels(playlist_filter)
        return [ch for ch in channels if getattr(ch, 'content_type', 'live') == content_type]
    
    # def refresh_content_counts(self):
    #     """Refresh content counts after playlist changes."""
    #     self._update_content_counts()
