"""Playlist model for M3U playlists."""
from dataclasses import dataclass, field
from typing import List, Optional
from .channel import Channel


@dataclass
class Playlist:
    """Represents an M3U playlist."""
    
    name: str
    source: str  # URL or file path
    channels: List[Channel] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # Store provider info (e.g. Xtream creds)
    
    def get_groups(self) -> List[str]:
        """Get all unique group names from channels."""
        groups = set()
        for channel in self.channels:
            if channel.group:
                groups.add(channel.group)
        return sorted(list(groups))
    
    def get_channels_by_group(self, group: str) -> List[Channel]:
        """Get channels filtered by group."""
        return [ch for ch in self.channels if ch.group == group]
    
    def get_favorites(self) -> List[Channel]:
        """Get all favorite channels."""
        return [ch for ch in self.channels if ch.is_favorite]
    
    def search_channels(self, query: str) -> List[Channel]:
        """Search channels by name."""
        query = query.lower()
        return [ch for ch in self.channels if query in ch.name.lower()]
    
    def to_dict(self) -> dict:
        """Convert playlist to dictionary for serialization."""
        return {
            "name": self.name,
            "source": self.source,
            "channels": [ch.to_dict() for ch in self.channels],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Playlist":
        """Create playlist from dictionary."""
        return cls(
            name=data.get("name", "Unknown Playlist"),
            source=data.get("source", ""),
            channels=[Channel.from_dict(ch) for ch in data.get("channels", [])],
        )
