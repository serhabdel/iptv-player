"""Channel model for IPTV channels."""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Channel:
    """Represents an IPTV channel."""
    
    name: str
    url: str
    logo: Optional[str] = None
    group: str = "Uncategorized"
    tvg_id: Optional[str] = None
    tvg_name: Optional[str] = None
    is_favorite: bool = False
    # New fields for enhanced features
    content_type: str = "live"  # "live", "movie", "series"
    audio_tracks: List[dict] = field(default_factory=list)  # [{"lang": "en", "codec": "aac"}]
    subtitle_tracks: List[dict] = field(default_factory=list)  # [{"lang": "en", "type": "embedded"}]
    last_watched: Optional[datetime] = None
    epg_channel_id: Optional[str] = None
    # Series-specific fields
    series_id: Optional[str] = None
    series_name: Optional[str] = None  # Normalized series name for grouping
    season: Optional[int] = None
    episode: Optional[int] = None
    
    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, other):
        if isinstance(other, Channel):
            return self.url == other.url
        return False
    
    def to_dict(self) -> dict:
        """Convert channel to dictionary for serialization."""
        return {
            "name": self.name,
            "url": self.url,
            "logo": self.logo,
            "group": self.group,
            "tvg_id": self.tvg_id,
            "tvg_name": self.tvg_name,
            "is_favorite": self.is_favorite,
            "content_type": self.content_type,
            "audio_tracks": self.audio_tracks,
            "subtitle_tracks": self.subtitle_tracks,
            "last_watched": self.last_watched.isoformat() if self.last_watched else None,
            "epg_channel_id": self.epg_channel_id,
            "series_id": self.series_id,
            "season": self.season,
            "episode": self.episode,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Channel":
        """Create channel from dictionary."""
        last_watched = None
        if data.get("last_watched"):
            try:
                last_watched = datetime.fromisoformat(data["last_watched"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            name=data.get("name", "Unknown"),
            url=data.get("url", ""),
            logo=data.get("logo"),
            group=data.get("group", "Uncategorized"),
            tvg_id=data.get("tvg_id"),
            tvg_name=data.get("tvg_name"),
            is_favorite=data.get("is_favorite", False),
            content_type=data.get("content_type", "live"),
            audio_tracks=data.get("audio_tracks", []),
            subtitle_tracks=data.get("subtitle_tracks", []),
            last_watched=last_watched,
            epg_channel_id=data.get("epg_channel_id"),
            series_id=data.get("series_id"),
            season=data.get("season"),
            episode=data.get("episode"),
        )
