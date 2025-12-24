"""M3U/M3U8 playlist parser with support for large files and content type detection."""
import re
import httpx
import aiofiles
from typing import List, Optional, Callable
from ..models.channel import Channel
from ..models.playlist import Playlist


class M3UParser:
    """Parser for M3U and M3U8 playlist files - optimized for large files."""
    
    # Extended timeout for large files
    TIMEOUT = 120.0  # 2 minutes
    MAX_RETRIES = 3
    CHUNK_SIZE = 65536  # 64KB chunks
    
    # Content type detection patterns
    MOVIE_GROUP_PATTERNS = [
        r'\bvod\b', r'\bmovie', r'\bfilm', r'\bcinema', r'\bafflam',
        r'\b4k\s*movies?\b', r'\bhd\s*movies?\b', r'\blatest\s*movies?\b',
        r'\bnew\s*movies?\b', r'\baction\b', r'\bcomedy\b', r'\bdrama\b',
        r'\bhorror\b', r'\bthriller\b', r'\bromance\b', r'\bsci-?fi\b',
        r'\bdocumentary\b', r'\banimation\b', r'\bfamily\b', r'\badventure\b',
        r'\bwestern\b', r'\bmusical\b', r'\bwar\b', r'\bcrime\b', r'\bmystery\b',
        r'\bfantasy\b', r'\bkids\s*movies?\b', r'\b\d{4}\b',  # Years like 2023, 2024
    ]
    
    SERIES_GROUP_PATTERNS = [
        r'\bseries\b', r'\btv\s*show', r'\bshow', r'\bepisode', r'\bseason',
        r'\bmosalsal', r'\bمسلسل', r'\bsitcom\b', r'\bdrama\s*series\b',
        r'\bnetflix\b', r'\bamazon\b', r'\bhbo\b', r'\bdisney\b', r'\bapple\s*tv\b',
        r'\bhulu\b', r'\bprime\b', r'\bparamount\b', r'\bpeacock\b',
        r'\boriginal\s*series\b', r'\bweb\s*series\b', r'\bmini\s*series\b',
        r'\banime\s*series\b', r'\bk-?drama\b', r'\btelenovela\b',
    ]
    
    LIVE_GROUP_PATTERNS = [
        r'\blive\b', r'\btv\b', r'\bchannel', r'\bnews\b', r'\bsport',
        r'\bmusic\b', r'\bkids\b', r'\breligious\b', r'\bislam',
        r'\bentertainment\b', r'\bgeneral\b', r'\bnational\b', r'\blocal\b',
        r'\bregional\b', r'\binternational\b', r'\bworld\b', r'\b24\/?7\b',
        r'\bfta\b', r'\bfree\s*to\s*air\b', r'\biptv\b', r'\bhevc\b', r'\bfhd\b',
        r'\buhd\b', r'\bsd\b', r'\bhd\b', r'\bpay\s*per\s*view\b', r'\bppv\b',
    ]
    
    # Series episode patterns in names
    SERIES_NAME_PATTERNS = [
        r's\d{1,2}\s*e\d{1,2}',  # S01E01, S1E1
        r'season\s*\d+',         # Season 1
        r'episode\s*\d+',        # Episode 1
        r'ep\s*\d+',             # Ep 1
        r'\bse?\d{1,2}\.?e?\d{1,2}\b',  # S01.E01, S1.1
        r'\[\d+x\d+\]',          # [1x01]
        r'e\d{2,3}\b',           # E01, E001
    ]
    
    # Movie patterns in names (years, quality)
    MOVIE_NAME_PATTERNS = [
        r'\(\d{4}\)',            # (2023)
        r'\[\d{4}\]',            # [2023]
        r'\b(19|20)\d{2}\b',     # 1990-2099
        r'\b(720p|1080p|2160p|4k|hdr)\b',
        r'\b(bluray|bdrip|webrip|hdtv|dvdrip)\b',
    ]
    
    @classmethod
    async def parse_from_url(
        cls, 
        url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Playlist:
        """Parse an M3U playlist from a URL with retry logic."""
        content = None
        last_error = None
        
        for attempt in range(cls.MAX_RETRIES):
            try:
                # Configure client with extended timeout and limits
                limits = httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                )
                timeout = httpx.Timeout(cls.TIMEOUT, connect=30.0)
                
                async with httpx.AsyncClient(
                    timeout=timeout,
                    limits=limits,
                    follow_redirects=True,
                ) as client:
                    # Stream the response for large files
                    async with client.stream('GET', url) as response:
                        response.raise_for_status()
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        chunks = []
                        
                        async for chunk in response.aiter_bytes(chunk_size=cls.CHUNK_SIZE):
                            chunks.append(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)
                        
                        content = b''.join(chunks).decode('utf-8', errors='ignore')
                        break  # Success, exit retry loop
                        
            except httpx.TimeoutException:
                last_error = f"Timeout (attempt {attempt + 1}/{cls.MAX_RETRIES})"
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                break  # Don't retry on HTTP errors
            except Exception as e:
                last_error = str(e)
            
            # Wait before retry
            if attempt < cls.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(2)
        
        if content is None:
            raise Exception(f"Failed to download playlist: {last_error}")
        
        # Parse the content
        channels = cls._parse_content(content)
        
        # Create playlist
        name = cls._extract_playlist_name(url, content)
        
        return Playlist(
            name=name,
            source=url,
            channels=channels
        )
    
    @classmethod
    async def parse_from_file(cls, file_path: str) -> Playlist:
        """Parse an M3U playlist from a local file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")
        
        channels = cls._parse_content(content)
        
        # Extract name from filename
        import os
        name = os.path.splitext(os.path.basename(file_path))[0]
        
        return Playlist(
            name=name,
            source=file_path,
            channels=channels
        )
    
    @classmethod
    def _parse_content(cls, content: str) -> List[Channel]:
        """Parse M3U content and return list of channels."""
        channels = []
        lines = content.splitlines()
        
        current_extinf = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if not line:
                continue
            
            # Check for EXTINF line
            if line.startswith('#EXTINF:'):
                current_extinf = line
                continue
            
            # Check for URL line (after EXTINF)
            if current_extinf and not line.startswith('#'):
                # This is a stream URL
                channel = cls._parse_channel(current_extinf, line)
                if channel:
                    channels.append(channel)
                current_extinf = None
        
        return channels
    
    @classmethod
    def _detect_content_type(cls, name: str, group: str, url: str) -> str:
        """Detect content type based on name, group, and URL patterns."""
        name_lower = name.lower()
        group_lower = group.lower()
        url_lower = url.lower()
        
        # Check URL patterns first (most reliable for some providers)
        if '/movie/' in url_lower or '/vod/' in url_lower:
            return 'movie'
        if '/series/' in url_lower or '/episode/' in url_lower:
            return 'series'
        if '/live/' in url_lower:
            return 'live'
        
        # Check for series patterns in name (high priority)
        for pattern in cls.SERIES_NAME_PATTERNS:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return 'series'
        
        # Check group patterns for series
        for pattern in cls.SERIES_GROUP_PATTERNS:
            if re.search(pattern, group_lower, re.IGNORECASE):
                return 'series'
        
        # Check for movie patterns in name
        movie_indicators = 0
        for pattern in cls.MOVIE_NAME_PATTERNS:
            if re.search(pattern, name_lower, re.IGNORECASE):
                movie_indicators += 1
        
        # Check group patterns for movies
        for pattern in cls.MOVIE_GROUP_PATTERNS:
            if re.search(pattern, group_lower, re.IGNORECASE):
                # If group contains movie patterns and not live patterns
                is_live = any(re.search(p, group_lower, re.IGNORECASE) for p in cls.LIVE_GROUP_PATTERNS[:6])
                if not is_live:
                    return 'movie'
        
        # If multiple movie indicators in name and no clear live patterns
        if movie_indicators >= 2:
            return 'movie'
        
        # Check group patterns for live TV
        for pattern in cls.LIVE_GROUP_PATTERNS:
            if re.search(pattern, group_lower, re.IGNORECASE):
                return 'live'
        
        # Default to live for anything else (traditional TV channels)
        return 'live'
    
    @classmethod
    def _parse_channel(cls, extinf_line: str, url: str) -> Optional[Channel]:
        """Parse a single channel from EXTINF line and URL."""
        try:
            # Extract the channel name - it's after the last comma
            # Format: #EXTINF:-1 tvg-id="..." tvg-name="..." group-title="...",Channel Name
            
            # Find the last comma - everything after is the channel name
            last_comma_idx = extinf_line.rfind(',')
            if last_comma_idx != -1:
                name = extinf_line[last_comma_idx + 1:].strip()
            else:
                name = ""
            
            # If name is empty or still contains attributes, try tvg-name
            if not name or 'tvg-' in name.lower() or '="' in name:
                # Try tvg-name attribute
                tvg_name_match = re.search(r'tvg-name="([^"]*)"', extinf_line, re.IGNORECASE)
                if tvg_name_match and tvg_name_match.group(1):
                    name = tvg_name_match.group(1)
            
            # Still empty? Try getting text from any attribute
            if not name or 'tvg-' in name.lower():
                # Last resort - try to find any readable name
                # Look for the actual display name after attributes
                match = re.search(r',\s*([^,]+)$', extinf_line)
                if match:
                    potential_name = match.group(1).strip()
                    if potential_name and 'tvg-' not in potential_name.lower():
                        name = potential_name
            
            # Clean up the name
            if name:
                # Remove any remaining attribute-like patterns
                name = re.sub(r'tvg-\w+="[^"]*"', '', name).strip()
                name = re.sub(r'\s+', ' ', name).strip()
            
            if not name:
                name = "Unknown Channel"
            
            # Extract logo - check both tvg-logo and logo
            logo = ""
            logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line, re.IGNORECASE)
            if logo_match:
                logo = logo_match.group(1)
            else:
                logo_match = re.search(r'logo="([^"]*)"', extinf_line, re.IGNORECASE)
                if logo_match:
                    logo = logo_match.group(1)
            
            # Extract group
            group = "Uncategorized"
            group_match = re.search(r'group-title="([^"]*)"', extinf_line, re.IGNORECASE)
            if group_match and group_match.group(1):
                group = group_match.group(1)
            
            # Extract tvg-id for EPG
            tvg_id = ""
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf_line, re.IGNORECASE)
            if tvg_id_match:
                tvg_id = tvg_id_match.group(1)
            
            # Detect content type
            content_type = cls._detect_content_type(name, group, url)
            
            # Extract series info if applicable
            series_id = None
            season = None
            episode = None
            
            if content_type == 'series':
                # Try to extract season/episode
                se_match = re.search(r's(\d{1,2})\s*e(\d{1,2})', name, re.IGNORECASE)
                if se_match:
                    season = int(se_match.group(1))
                    episode = int(se_match.group(2))
                    # Extract series name: everything before SxxExx
                    series_name = name[:se_match.start()].strip()
                    # Clean up series name 
                    series_name = re.sub(r'[.\-_]', ' ', series_name).strip()
                    series_name = re.sub(r'\s+', ' ', series_name).title()
                else:
                    # Try season pattern
                    season_match = re.search(r'season\s*(\d+)', name, re.IGNORECASE)
                    if season_match:
                        season = int(season_match.group(1))
                        # Series name might be before "Season X"
                        series_name = name[:season_match.start()].strip()
                    
                    # Try episode pattern
                    ep_match = re.search(r'(?:episode|ep)\s*(\d+)', name, re.IGNORECASE)
                    if ep_match:
                        episode = int(ep_match.group(1))
                        if not season: # If we haven't found season yet
                             # Maybe just before episode?
                             if not series_name:
                                 series_name = name[:ep_match.start()].strip()

            # Clean series name if found
            if 'series_name' in locals() and series_name:
                 # Remove common prefixes/suffixes
                 pass
            else:
                 # If no series name extracted but identified as series, use group or part of name
                 if content_type == 'series':
                     series_name = name
                     # Try to remove episode info manually if regex failed
                     series_name = re.sub(r'E\d+', '', series_name).strip()
                     series_name = re.sub(r'\d{4}', '', series_name).strip() # Remove year

            # Ensure normalized series name
            if 'series_name' not in locals() or not series_name:
                 series_name = name
            
            return Channel(
                name=name,
                url=url,
                logo=logo,
                group=group,
                is_favorite=False,
                content_type=content_type,
                tvg_id=tvg_id,
                epg_channel_id=tvg_id,
                series_id=series_id,
                series_name=series_name,
                season=season,
                episode=episode,
            )
            
        except Exception:
            return None
    
    @classmethod
    def _extract_playlist_name(cls, url: str, content: str) -> str:
        """Extract playlist name from URL or content."""
        import os
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        path = parsed.path
        
        if path:
            filename = os.path.basename(path)
            name = os.path.splitext(filename)[0]
            if name and name != "get" and len(name) > 2:
                return name
        
        return parsed.netloc or "Playlist"
