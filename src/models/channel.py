"""Channel model for IPTV channels."""
from dataclasses import dataclass, field
from typing import Optional


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
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Channel":
        """Create channel from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            url=data.get("url", ""),
            logo=data.get("logo"),
            group=data.get("group", "Uncategorized"),
            tvg_id=data.get("tvg_id"),
            tvg_name=data.get("tvg_name"),
            is_favorite=data.get("is_favorite", False),
        )
