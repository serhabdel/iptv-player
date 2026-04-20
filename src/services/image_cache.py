"""Image caching service for channel logos and thumbnails."""
import os
import sys
import hashlib
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, List
from functools import lru_cache


def _default_cache_dir() -> Path:
    """Get platform-appropriate cache directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
        return base / "iptv-player" / "image_cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "iptv-player" / "images"
    else:
        return Path(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))) / "iptv-player" / "images"


class ImageCache:
    """LRU-based image cache for channel logos."""
    
    _instance: Optional['ImageCache'] = None
    
    # Shared session for connection pooling
    _session: Optional[aiohttp.ClientSession] = None
    _download_semaphore: Optional[asyncio.Semaphore] = None
    
    def __init__(self, cache_dir: Optional[str] = None, max_size_mb: int = 100):
        self._cache_dir = Path(cache_dir) if cache_dir else _default_cache_dir()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._memory_cache: dict[str, str] = {}  # url -> local_path
        self._max_memory_items = 500
        
    @classmethod
    def get_instance(cls) -> 'ImageCache':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = ImageCache()
        return cls._instance
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, url: str) -> Path:
        """Get local cache path for URL."""
        key = self._get_cache_key(url)
        # Preserve extension from URL if possible
        ext = ".png"
        if "." in url.split("/")[-1]:
            url_ext = url.split(".")[-1].split("?")[0].lower()
            if url_ext in ["png", "jpg", "jpeg", "webp", "gif"]:
                ext = f".{url_ext}"
        return self._cache_dir / f"{key}{ext}"
    
    def get_cached(self, url: str) -> Optional[str]:
        """Get cached image path if exists."""
        if not url:
            return None
            
        # Check memory cache first
        if url in self._memory_cache:
            path = self._memory_cache[url]
            if os.path.exists(path):
                return path
        
        # Check disk cache
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            # Add to memory cache
            self._memory_cache[url] = str(cache_path)
            self._trim_memory_cache()
            return str(cache_path)
        
        return None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a shared HTTP session for connection pooling."""
        if ImageCache._session is None or ImageCache._session.closed:
            connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)
            ImageCache._session = aiohttp.ClientSession(connector=connector)
        return ImageCache._session
    
    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get download concurrency limiter."""
        if ImageCache._download_semaphore is None:
            ImageCache._download_semaphore = asyncio.Semaphore(8)
        return ImageCache._download_semaphore

    async def get_or_download(self, url: str, timeout: int = 10) -> Optional[str]:
        """Get cached image or download it."""
        if not url:
            return None
            
        # Check cache first
        cached = self.get_cached(url)
        if cached:
            return cached
        
        # Download and cache with concurrency limit
        sem = await self._get_semaphore()
        async with sem:
            try:
                cache_path = self._get_cache_path(url)
                session = await self._get_session()
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(cache_path, 'wb') as f:
                            await f.write(content)
                        
                        # Add to memory cache
                        self._memory_cache[url] = str(cache_path)
                        self._trim_memory_cache()
                        
                        return str(cache_path)
            except Exception as e:
                pass  # Silently ignore download failures for logos
        
        return None
    
    async def batch_download(self, urls: List[str], timeout: int = 8) -> dict:
        """Download multiple images concurrently. Returns {url: local_path}."""
        results = {}
        tasks = []
        for url in urls:
            if not url:
                continue
            cached = self.get_cached(url)
            if cached:
                results[url] = cached
            else:
                tasks.append(self._download_single(url, timeout))
        
        if tasks:
            done = await asyncio.gather(*tasks, return_exceptions=True)
            for result in done:
                if isinstance(result, tuple):
                    url, path = result
                    if path:
                        results[url] = path
        return results
    
    async def _download_single(self, url: str, timeout: int) -> tuple:
        """Download a single image, returns (url, path_or_None)."""
        path = await self.get_or_download(url, timeout)
        return (url, path)
    
    def _trim_memory_cache(self):
        """Trim memory cache if too large."""
        if len(self._memory_cache) > self._max_memory_items:
            # Remove first 10% of items (oldest)
            items_to_remove = len(self._memory_cache) // 10
            keys_to_remove = list(self._memory_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self._memory_cache[key]
    
    async def cleanup_old_files(self, max_age_days: int = 7):
        """Remove cached files older than max_age_days."""
        import time
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = time.time()
        
        for file in self._cache_dir.iterdir():
            if file.is_file():
                file_age = current_time - file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file.unlink()
                    except Exception:
                        pass
    
    def clear_cache(self):
        """Clear all cached images."""
        self._memory_cache.clear()
        for file in self._cache_dir.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                except Exception:
                    pass


# Convenience function
def get_image_cache() -> ImageCache:
    """Get the global image cache instance."""
    return ImageCache.get_instance()
