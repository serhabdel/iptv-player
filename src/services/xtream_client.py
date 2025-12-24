"""Xtream Codes API client for IPTV providers."""
import httpx
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from ..models.channel import Channel


@dataclass
class XtreamCredentials:
    """Xtream Codes API credentials."""
    name: str
    server: str  # e.g., http://example.com:8080
    username: str
    password: str
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "server": self.server,
            "username": self.username,
            "password": self.password,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "XtreamCredentials":
        return cls(
            name=data.get("name", "Xtream Provider"),
            server=data.get("server", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
        )


@dataclass
class XtreamAccountInfo:
    """Xtream Codes account information."""
    username: str
    status: str
    exp_date: Optional[str]
    is_trial: bool
    active_cons: int
    max_connections: int
    created_at: Optional[str]


@dataclass
class XtreamCategory:
    """Xtream Codes category."""
    category_id: str
    category_name: str
    parent_id: int = 0


class XtreamCodesClient:
    """Client for Xtream Codes API."""
    
    TIMEOUT = 60.0
    
    # Headers to mimic a TV/media player app
    DEFAULT_HEADERS = {
        "User-Agent": "IPTV Smarters Pro/2.2.2.5 (Linux; Android 10)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    
    def __init__(self, credentials: XtreamCredentials):
        self.credentials = credentials
        # Normalize the server URL
        server = credentials.server.strip().rstrip('/')
        # Add http:// if no protocol specified
        if not server.startswith('http://') and not server.startswith('https://'):
            server = f'http://{server}'
        self._base_url = server
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create configured HTTP client."""
        return httpx.AsyncClient(
            timeout=self.TIMEOUT,
            follow_redirects=True,
            headers=self.DEFAULT_HEADERS,
            verify=False,  # Some IPTV servers have invalid SSL certs
            http2=False,   # Force HTTP/1.1 for better compatibility
        )
    
    def _get_api_url(self, action: str, extra_params: Optional[Dict[str, str]] = None) -> str:
        """Build API URL with authentication."""
        url = f"{self._base_url}/player_api.php"
        params = f"username={self.credentials.username}&password={self.credentials.password}&action={action}"
        if extra_params:
            for key, value in extra_params.items():
                params += f"&{key}={value}"
        return f"{url}?{params}"
    
    async def authenticate(self) -> XtreamAccountInfo:
        """Test connection and get account information."""
        url = f"{self._base_url}/player_api.php?username={self.credentials.username}&password={self.credentials.password}"
        
        try:
            async with self._create_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            raise Exception(f"Cannot connect to server: {self._base_url}") from e
        except httpx.TimeoutException:
            raise Exception(f"Connection timed out after {self.TIMEOUT}s")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Server returned error {e.response.status_code}") from e
        except Exception as e:
            raise Exception(f"Connection error: {type(e).__name__} - {str(e) or 'Unknown error'}") from e
        
        if "user_info" not in data:
            raise Exception(f"Invalid response: expected 'user_info' in response. Got keys: {list(data.keys())}")
        
        user_info = data["user_info"]
        
        # Check for authentication errors
        status = user_info.get("status", "")
        if status.lower() in ["disabled", "banned", "expired"]:
            raise Exception(f"Account status: {status}")
        
        return XtreamAccountInfo(
            username=user_info.get("username", ""),
            status=user_info.get("status", "Unknown"),
            exp_date=user_info.get("exp_date"),
            is_trial=str(user_info.get("is_trial", "0")) == "1",
            active_cons=int(user_info.get("active_cons", 0)),
            max_connections=int(user_info.get("max_connections", 1)),
            created_at=user_info.get("created_at"),
        )
    
    async def get_live_categories(self) -> List[XtreamCategory]:
        """Get all live stream categories."""
        url = self._get_api_url("get_live_categories")
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        categories = []
        for item in data:
            categories.append(XtreamCategory(
                category_id=str(item.get("category_id", "")),
                category_name=item.get("category_name", "Unknown"),
                parent_id=int(item.get("parent_id", 0)),
            ))
        return categories
    
    async def get_live_streams(self, category_id: Optional[str] = None) -> List[Channel]:
        """Get live streams, optionally filtered by category."""
        extra_params = {"category_id": category_id} if category_id else None
        url = self._get_api_url("get_live_streams", extra_params)
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        channels = []
        for item in data:
            stream_id = item.get("stream_id", "")
            # Build the stream URL
            stream_url = f"{self._base_url}/live/{self.credentials.username}/{self.credentials.password}/{stream_id}.ts"
            
            channels.append(Channel(
                name=item.get("name", "Unknown"),
                url=stream_url,
                logo=item.get("stream_icon", ""),
                group=item.get("category_name", "Live TV"),
                tvg_id=item.get("epg_channel_id"),
                tvg_name=item.get("name"),
                is_favorite=False,
                content_type="live",
            ))
        return channels
    
    async def get_vod_categories(self) -> List[XtreamCategory]:
        """Get all VOD categories."""
        url = self._get_api_url("get_vod_categories")
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        categories = []
        for item in data:
            categories.append(XtreamCategory(
                category_id=str(item.get("category_id", "")),
                category_name=item.get("category_name", "Unknown"),
                parent_id=int(item.get("parent_id", 0)),
            ))
        return categories
    
    async def get_vod_streams(self, category_id: Optional[str] = None) -> List[Channel]:
        """Get VOD streams, optionally filtered by category."""
        extra_params = {"category_id": category_id} if category_id else None
        url = self._get_api_url("get_vod_streams", extra_params)
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        channels = []
        for item in data:
            stream_id = item.get("stream_id", "")
            extension = item.get("container_extension", "mp4")
            # Build the VOD URL
            stream_url = f"{self._base_url}/movie/{self.credentials.username}/{self.credentials.password}/{stream_id}.{extension}"
            
            channels.append(Channel(
                name=item.get("name", "Unknown"),
                url=stream_url,
                logo=item.get("stream_icon", ""),
                group=f"VOD - {item.get('category_name', 'Movies')}",
                is_favorite=False,
                content_type="movie",
            ))
        return channels
    
    async def get_series_categories(self) -> List[XtreamCategory]:
        """Get all series categories."""
        url = self._get_api_url("get_series_categories")
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        categories = []
        for item in data:
            categories.append(XtreamCategory(
                category_id=str(item.get("category_id", "")),
                category_name=item.get("category_name", "Unknown"),
                parent_id=int(item.get("parent_id", 0)),
            ))
        return categories
    
    async def get_series(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get series list, optionally filtered by category."""
        extra_params = {"category_id": category_id} if category_id else None
        url = self._get_api_url("get_series", extra_params)
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        return data
    
    async def get_series_info(self, series_id: str) -> Dict[str, Any]:
        """Get detailed series information including episodes."""
        url = self._get_api_url("get_series_info", {"series_id": series_id})
        
        async with self._create_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        return data
    
    def build_series_episode_url(self, episode_id: str, extension: str = "mp4") -> str:
        """Build URL for a series episode."""
        return f"{self._base_url}/series/{self.credentials.username}/{self.credentials.password}/{episode_id}.{extension}"
    
    async def get_all_channels(self) -> List[Channel]:
        """Get all live streams, VODs, and Series."""
        live_task = self.get_live_streams()
        vod_task = self.get_vod_streams()
        series_task = self.get_series()
        
        import asyncio
        results = await asyncio.gather(live_task, vod_task, series_task, return_exceptions=True)
        
        channels = []
        # Process live results
        if isinstance(results[0], list):
            channels.extend(results[0])
        else:
            print(f"Error fetching live streams: {results[0]}")
            
        # Process VOD results
        if isinstance(results[1], list):
            channels.extend(results[1])
        else:
             print(f"Error fetching VOD streams: {results[1]}")

        # Process Series results
        if isinstance(results[2], list):
             for item in results[2]:
                 # Map series to a Channel object
                 # URL is a placeholder that identifies it as an Xtream series
                 series_id = item.get("series_id", "")
                 channels.append(Channel(
                     name=item.get("name", "Unknown Series"),
                     url=f"xtream://series/{series_id}",
                     logo=item.get("cover", ""),
                     group=f"Series - {item.get('category_name', 'Uncategorized')}",
                     is_favorite=False,
                     content_type="series",
                     series_id=str(series_id),
                     series_name=item.get("name", ""),
                 ))
        else:
             print(f"Error fetching Series: {results[2]}")
             
        return channels
