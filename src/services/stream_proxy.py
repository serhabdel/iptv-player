"""Local stream proxy server for casting to DLNA devices."""
import asyncio
import socket
from typing import Optional, Callable
from aiohttp import web, ClientSession, ClientTimeout
import threading
import uuid
from typing import Dict


class StreamProxyServer:
    """Local HTTP proxy server that relays IPTV streams for DLNA casting.
    
    Supports bandwidth throttling for testing purposes.
    """
    
    def __init__(self, port: int = 8899):
        self.port = port
        self._streams: Dict[str, str] = {}  # id -> url
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._running = False
        self._local_ip: Optional[str] = None
        
        # Bandwidth throttling (0 = unlimited)
        self._bandwidth_limit_kbps: float = 0  # KB/s limit
        self._throttle_enabled: bool = False
    
    def get_local_ip(self) -> str:
        """Get the local IP address of this machine."""
        if self._local_ip:
            return self._local_ip
        
        try:
            # Connect to external server to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._local_ip = ip
            return ip
        except Exception:
            return "127.0.0.1"
    
    def set_stream(self, stream_url: str) -> str:
        """Register a stream and return its proxy URL (Legacy/Simple)."""
        # For backward compatibility/simplicity, we clear old streams and set a 'default' one?
        # Actually, let's just register it with a fixed 'current' ID or new one.
        # Let's use a standard 'current' ID for simple usage.
        self._streams['current'] = stream_url
        local_ip = self.get_local_ip()
        return f"http://{local_ip}:{self.port}/stream/current"
        
    def register_stream(self, stream_url: str) -> str:
        """Register a new stream and return its unique proxy URL."""
        stream_id = str(uuid.uuid4())[:8]
        self._streams[stream_id] = stream_url
        local_ip = self.get_local_ip()
        return f"http://{local_ip}:{self.port}/stream/{stream_id}"

    def get_proxy_url(self) -> str:
        """Get the proxy URL for the 'current' stream."""
        local_ip = self.get_local_ip()
        return f"http://{local_ip}:{self.port}/stream/current"
    
    # ========================
    # Bandwidth Throttling API
    # ========================
    
    def set_bandwidth_limit(self, limit_kbps: float):
        """Set bandwidth limit in KB/s. Set to 0 for unlimited.
        
        Args:
            limit_kbps: Bandwidth limit in kilobytes per second
                       Common values: 500 (SD), 1000 (720p), 2500 (1080p), 5000 (4K)
        """
        self._bandwidth_limit_kbps = max(0, limit_kbps)
        self._throttle_enabled = limit_kbps > 0
        print(f"Bandwidth limit: {limit_kbps} KB/s" if limit_kbps > 0 else "Bandwidth: Unlimited")
    
    def set_bandwidth_limit_mbps(self, limit_mbps: float):
        """Set bandwidth limit in MB/s."""
        self.set_bandwidth_limit(limit_mbps * 1024)
    
    def get_bandwidth_limit(self) -> float:
        """Get current bandwidth limit in KB/s."""
        return self._bandwidth_limit_kbps
    
    def is_throttle_enabled(self) -> bool:
        """Check if bandwidth throttling is enabled."""
        return self._throttle_enabled
    
    def disable_throttle(self):
        """Disable bandwidth throttling."""
        self.set_bandwidth_limit(0)
    
    async def _handle_stream(self, request: web.Request) -> web.StreamResponse:
        """Handle stream requests by proxying the IPTV stream."""
        # Extract stream ID from path
        # /stream/{id} or /stream/{id}.ts etc
        path = request.path
        # Remove leading /stream/
        if path.startswith('/stream/'):
             clean_path = path[8:] # remove /stream/
        else:
             # Fallback for old /stream path if needed, though we changed route
             clean_path = 'current'

        # Remove extension
        stream_id = clean_path.split('.')[0]
        
        target_url = self._streams.get(stream_id)
        if not target_url:
            # Try fallback to 'current' if accessing root /stream (not caught by regex well?)
            target_url = self._streams.get('current')
            
        if not target_url:
            return web.Response(status=404, text=f"Stream {stream_id} not found")
        
        current_url = target_url # Local var for clarity
        
        # Handle HEAD requests (often used by TVs to check stream availability)
        if request.method == 'HEAD':
            return web.Response(
                status=200,
                headers={
                    'Content-Type': 'video/MP2T',
                    'Accept-Ranges': 'none',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                }
            )
        
        # Forward Range header if present (though many IPTV streams don't support it)
        headers = {}
        if 'Range' in request.headers:
            headers['Range'] = request.headers['Range']
        
        path = request.path
        content_type = 'video/MP2T'
        if path.endswith('.m3u8'):
            content_type = 'application/x-mpegURL'
        elif path.endswith('.mp4'):
            content_type = 'video/mp4'
        elif path.endswith('.mkv'):
            content_type = 'video/x-matroska'
            
        # Create streaming response
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': content_type,
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Transfer-Encoding': 'chunked',
            }
        )
        
        try:
            await response.prepare(request)
            
            # Stream from source to client
            timeout = ClientTimeout(total=None, connect=30, sock_read=60)
            
            async with ClientSession(timeout=timeout) as session:
                async with session.get(current_url, headers=headers) as upstream:
                    # Choose chunk size based on throttling
                    if self._throttle_enabled:
                        # Smaller chunks for better throttle precision
                        chunk_size = min(32 * 1024, int(self._bandwidth_limit_kbps * 1024 / 4))
                        chunk_size = max(chunk_size, 4096)  # Min 4KB
                    else:
                        # Large chunks for better throughput 
                        chunk_size = 1024 * 1024  # 1MB
                    
                    bytes_sent = 0
                    start_time = asyncio.get_event_loop().time()
                    
                    async for chunk in upstream.content.iter_chunked(chunk_size):
                        try:
                            # Throttle if enabled
                            if self._throttle_enabled and self._bandwidth_limit_kbps > 0:
                                bytes_sent += len(chunk)
                                elapsed = asyncio.get_event_loop().time() - start_time
                                
                                # Calculate expected time for bytes sent
                                expected_time = bytes_sent / (self._bandwidth_limit_kbps * 1024)
                                
                                # Sleep if we're ahead of schedule
                                if expected_time > elapsed:
                                    await asyncio.sleep(expected_time - elapsed)
                            
                            await response.write(chunk)
                        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
                            # Client disconnected, stop streaming
                            return response
                        except Exception:
                            # Other write error, stop streaming
                            return response
                            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Suppress "Cannot write to closing transport" and similar noise
            pass
        
        return response
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.Response(text="OK")
    
    async def start(self):
        """Start the proxy server."""
        if self._running:
            return
        
        self._app = web.Application()
        # Support various extensions for TV compatibility, with stream ID
        # Matches /stream/{id} and /stream/{id}.ts etc.
        self._app.router.add_get('/stream/{tail:.*}', self._handle_stream)
        self._app.router.add_get('/health', self._handle_health)
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        self._site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        await self._site.start()
        
        self._running = True
        print(f"Stream proxy running at http://{self.get_local_ip()}:{self.port}")
    
    async def stop(self):
        """Stop the proxy server."""
        if not self._running:
            return
        
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        
        self._running = False
        self._streams.clear()
    
    def is_running(self) -> bool:
        """Check if proxy is running."""
        return self._running


# Global instance
_proxy_instance: Optional[StreamProxyServer] = None


def get_stream_proxy() -> StreamProxyServer:
    """Get or create the global stream proxy instance."""
    global _proxy_instance
    if _proxy_instance is None:
        _proxy_instance = StreamProxyServer()
    return _proxy_instance
