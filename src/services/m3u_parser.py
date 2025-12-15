"""M3U/M3U8 playlist parser with support for large files."""
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
            
            return Channel(
                name=name,
                url=url,
                logo=logo,
                group=group,
                is_favorite=False
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
