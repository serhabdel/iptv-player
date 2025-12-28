"""DLNA/UPnP casting service for casting streams to Smart TVs."""
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Callable
import socket


@dataclass
class DLNADevice:
    """Represents a discovered DLNA device."""
    name: str
    location: str
    udn: str  # Unique Device Name
    device_type: str
    control_url: Optional[str] = None  # Added for subsequent controls
    rendering_control_url: Optional[str] = None  # Added for subsequent controls
    
    def __hash__(self):
        return hash(self.udn)
    
    def __eq__(self, other):
        if isinstance(other, DLNADevice):
            return self.udn == other.udn
        return False


class DLNACastService:
    """Service for discovering and casting to DLNA devices."""
    
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SEARCH_TARGET = "urn:schemas-upnp-org:device:MediaRenderer:1"
    TIMEOUT = 3.0
    
    def __init__(self):
        self._devices: List[DLNADevice] = []
        self._current_device: Optional[DLNADevice] = None
        self._discovery_callbacks: List[Callable] = []
        self._upnp_factory = None
        self._dmr_device = None
    
    async def discover_devices(self) -> List[DLNADevice]:
        """Discover DLNA MediaRenderer devices on the network."""
        self._devices.clear()
        
        try:
            # Use async-upnp-client for discovery
            from async_upnp_client.search import async_search
            from async_upnp_client.aiohttp import AiohttpRequester
            
            requester = AiohttpRequester()
            
            async def device_callback(data):
                """Handle discovered device."""
                try:
                    location = data.get("location", "")
                    usn = data.get("usn", "")
                    
                    # Extract UDN from USN
                    udn = usn.split("::")[0] if "::" in usn else usn
                    
                    # Get device name from location
                    name = await self._get_device_name(location, requester)
                    
                    device = DLNADevice(
                        name=name or "Unknown Device",
                        location=location,
                        udn=udn,
                        device_type="MediaRenderer",
                    )
                    
                    if device not in self._devices:
                        self._devices.append(device)
                        for callback in self._discovery_callbacks:
                            callback(device)
                            
                except Exception:
                    pass
            
            # Search for MediaRenderers
            await async_search(
                search_target=self.SEARCH_TARGET,
                timeout=self.TIMEOUT,
                async_callback=device_callback,
            )
            
        except ImportError:
            # Fallback to basic SSDP discovery without async-upnp-client
            await self._basic_ssdp_discovery()
        except Exception:
            await self._basic_ssdp_discovery()
        
        # Also try direct Samsung TV discovery (for TVs that don't respond to SSDP)
        await self._discover_samsung_tvs_direct()
        
        return self._devices
    
    async def _discover_samsung_tvs_direct(self):
        """Direct Samsung TV discovery by scanning known ports."""
        import httpx
        
        # Get local network prefix
        local_ip = self._get_local_ip()
        if not local_ip:
            return
        
        network_prefix = ".".join(local_ip.split(".")[:3]) + "."
        
        async def check_samsung_tv(ip: str):
            """Check if IP is a Samsung TV with DLNA support."""
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(1.0, connect=0.5)) as client:
                    # Check Samsung DLNA DMR endpoint
                    dmr_url = f"http://{ip}:9197/dmr"
                    response = await client.get(dmr_url)
                    
                    if response.status_code == 200 and "MediaRenderer" in response.text:
                        # Parse the device info
                        import re
                        name_match = re.search(r'<friendlyName>([^<]+)</friendlyName>', response.text)
                        udn_match = re.search(r'<UDN>([^<]+)</UDN>', response.text)
                        
                        name = name_match.group(1) if name_match else f"Samsung TV ({ip})"
                        udn = udn_match.group(1) if udn_match else f"uuid:{ip}"
                        
                        device = DLNADevice(
                            name=name,
                            location=dmr_url,
                            udn=udn,
                            device_type="MediaRenderer",
                        )
                        
                        if device not in self._devices:
                            self._devices.append(device)
                            for callback in self._discovery_callbacks:
                                callback(device)
                            print(f"Found Samsung TV: {name} @ {ip}")
            except Exception:
                pass
        
        # Scan all IPs in the network simultaneously in chunks
        all_ips = [f"{network_prefix}{i}" for i in range(1, 255)]
        
        # Scan in larger batches for speed
        batch_size = 64
        for i in range(0, len(all_ips), batch_size):
            batch = all_ips[i:i + batch_size]
            await asyncio.gather(*[check_samsung_tv(ip) for ip in batch], return_exceptions=True)
    
    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return ""
    
    async def _get_device_name(self, location: str, requester=None) -> Optional[str]:
        """Get device friendly name from its description XML."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(location)
                xml_content = response.text
                
                # Simple XML parsing for friendly name
                import re
                match = re.search(r'<friendlyName>([^<]+)</friendlyName>', xml_content)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None
    
    async def _basic_ssdp_discovery(self):
        """Basic SSDP discovery fallback."""
        try:
            # M-SEARCH message
            message = (
                'M-SEARCH * HTTP/1.1\r\n'
                f'HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n'
                'MAN: "ssdp:discover"\r\n'
                f'MX: {int(self.TIMEOUT)}\r\n'
                f'ST: {self.SEARCH_TARGET}\r\n'
                '\r\n'
            ).encode('utf-8')
            
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(self.TIMEOUT)
            
            try:
                sock.sendto(message, (self.SSDP_ADDR, self.SSDP_PORT))
                
                end_time = asyncio.get_event_loop().time() + self.TIMEOUT
                
                while asyncio.get_event_loop().time() < end_time:
                    try:
                        data, addr = sock.recvfrom(4096)
                        await self._parse_ssdp_response(data.decode('utf-8'))
                    except socket.timeout:
                        break
                    except Exception:
                        continue
            finally:
                sock.close()
                
        except Exception:
            pass
    
    async def _parse_ssdp_response(self, response: str):
        """Parse SSDP response and add device."""
        try:
            lines = response.split('\r\n')
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.upper().strip()] = value.strip()
            
            location = headers.get('LOCATION', '')
            usn = headers.get('USN', '')
            
            if location and usn:
                udn = usn.split('::')[0] if '::' in usn else usn
                name = await self._get_device_name(location)
                
                device = DLNADevice(
                    name=name or f"Device ({location.split('/')[2]})",
                    location=location,
                    udn=udn,
                    device_type="MediaRenderer",
                )
                
                if device not in self._devices:
                    self._devices.append(device)
                    
        except Exception:
            pass
    
    async def cast_to_device(self, device: DLNADevice, stream_url: str, title: str = "IPTV Stream") -> bool:
        """Cast a stream URL to a DLNA device."""
        # Try raw UPnP first as it has better Samsung TV compatibility
        success = await self._raw_upnp_cast(device, stream_url, title)
        if success:
            return True
        
        # Fallback to async-upnp-client
        try:
            from async_upnp_client.aiohttp import AiohttpRequester
            from async_upnp_client.client_factory import UpnpFactory
            from async_upnp_client.profiles.dlna import DmrDevice
            
            requester = AiohttpRequester()
            factory = UpnpFactory(requester)
            
            # Get the device
            upnp_device = await factory.async_create_device(device.location)
            dmr_device = DmrDevice(upnp_device, None)
            
            # Generate DIDL-Lite metadata
            didl_metadata = self._generate_didl_metadata(stream_url, title)
            
            # Set the stream URL with metadata
            await dmr_device.async_set_transport_uri(
                stream_url,
                title,
                meta_data=didl_metadata,
            )
            
            # Start playback
            await dmr_device.async_play()
            
            self._current_device = device
            self._dmr_device = dmr_device
            
            return True
            
        except Exception as e:
            print(f"Cast error: {e}")
            return False
    
    def _generate_didl_metadata(self, stream_url: str, title: str) -> str:
        """Generate DIDL-Lite metadata for the stream."""
        import html
        
        # Escape XML special characters
        safe_url = html.escape(stream_url)
        safe_title = html.escape(title)
        
        # Determine MIME type based on URL
        if ".m3u8" in stream_url.lower():
            mime_type = "application/x-mpegURL"
            protocol_info = "http-get:*:application/x-mpegURL:*"
        elif ".ts" in stream_url.lower():
            mime_type = "video/MP2T"
            protocol_info = "http-get:*:video/MP2T:DLNA.ORG_OP=01;DLNA.ORG_FLAGS=01700000000000000000000000000000"
        elif ".mp4" in stream_url.lower():
            mime_type = "video/mp4"
            protocol_info = "http-get:*:video/mp4:DLNA.ORG_OP=01;DLNA.ORG_FLAGS=01700000000000000000000000000000"
        else:
            # Default: assume MPEG-TS stream for IPTV
            mime_type = "video/MP2T"
            protocol_info = "http-get:*:video/MP2T:*"
        
        didl = f'''<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="0" parentID="-1" restricted="1">
    <dc:title>{safe_title}</dc:title>
    <upnp:class>object.item.videoItem.videoBroadcast</upnp:class>
    <res protocolInfo="{protocol_info}">{safe_url}</res>
  </item>
</DIDL-Lite>'''
        
        return didl
    
    async def _raw_upnp_cast(self, device: DLNADevice, stream_url: str, title: str) -> bool:
        """Raw UPnP SOAP casting with Samsung TV compatibility."""
        try:
            import httpx
            import html
            
            # Try to stop previous playback first (helps with Samsung TV stability)
            try:
                if device.control_url:
                    await self._send_soap_action(
                        device.control_url,
                        "Stop",
                        '''<u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"><InstanceID>0</InstanceID></u:Stop>'''
                    )
            except Exception:
                pass

            # First get the device description to find control URL
            control_url = None
            if device.control_url:
                control_url = device.control_url
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(device.location)
                    xml_content = response.text
                
                # Parse for AVTransport control URL
                import re
                base_url = '/'.join(device.location.split('/')[:3])
                
                # Find AVTransport control URL
                control_match = re.search(
                    r'<serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>.*?<controlURL>([^<]+)</controlURL>',
                    xml_content,
                    re.DOTALL
                )
                
                if control_match:
                    url_part = control_match.group(1)
                    if url_part.startswith('http'):
                        control_url = url_part
                    else:
                        if not url_part.startswith('/'):
                            url_part = '/' + url_part
                        control_url = base_url + url_part
                    
                    # Cache it
                    device.control_url = control_url
                
                # Find RenderingControl URL
                render_match = re.search(
                    r'<serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>.*?<controlURL>([^<]+)</controlURL>',
                    xml_content,
                    re.DOTALL
                )
                
                if render_match:
                    url_part = render_match.group(1)
                    if url_part.startswith('http'):
                        device.rendering_control_url = url_part
                    else:
                        if not url_part.startswith('/'):
                            url_part = '/' + url_part
                        device.rendering_control_url = base_url + url_part
            
            if not control_url:
                return False
            
            # Escape for XML
            safe_url = html.escape(stream_url)
            safe_title = html.escape(title)
            
            # Determine protocol info based on stream type
            if ".m3u8" in stream_url.lower():
                protocol_info = "http-get:*:application/x-mpegURL:*"
            elif ".ts" in stream_url.lower():
                protocol_info = "http-get:*:video/MP2T:DLNA.ORG_OP=01;DLNA.ORG_FLAGS=01700000000000000000000000000000"
            else:
                protocol_info = "http-get:*:video/MP2T:*"
            
            # DIDL-Lite metadata (required by Samsung)
            didl_metadata = f'''&lt;DIDL-Lite xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot; xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot;&gt;&lt;item id=&quot;0&quot; parentID=&quot;-1&quot; restricted=&quot;1&quot;&gt;&lt;dc:title&gt;{safe_title}&lt;/dc:title&gt;&lt;upnp:class&gt;object.item.videoItem.videoBroadcast&lt;/upnp:class&gt;&lt;res protocolInfo=&quot;{protocol_info}&quot;&gt;{safe_url}&lt;/res&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;'''
            
            # SetAVTransportURI SOAP envelope with metadata
            set_uri_body = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{safe_url}</CurrentURI>
      <CurrentURIMetaData>{didl_metadata}</CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"',
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(control_url, content=set_uri_body, headers=headers)
                
                if response.status_code != 200:
                    print(f"SetAVTransportURI failed: {response.status_code} - {response.text[:200]}")
                    return False
            
            # Play SOAP envelope
            play_body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>'''
            
            headers['SOAPAction'] = '"urn:schemas-upnp-org:service:AVTransport:1#Play"'
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(control_url, content=play_body, headers=headers)
                
                if response.status_code == 200:
                    self._current_device = device
                    return True
            
            return False
            
        except Exception as e:
            print(f"Raw UPnP cast error: {e}")
            return False

    
    async def stop_casting(self) -> bool:
        """Stop casting to current device."""
        if not self._current_device:
            return False
        
        try:
            if self._dmr_device:
                await self._dmr_device.async_stop()
            else:
                await self._raw_upnp_stop()
            if self._raw_upnp_client:
                # TODO: Implement raw UPnP mute if needed
                pass
            
            self._current_device = None
            self._dmr_device = None
            return True
            
        except Exception:
            return False

    async def set_next_av_transport_uri(self, uri: str, title: str) -> bool:
        """Set the NextAVTransportURI for gapless/playlist playback."""
        if not self._current_device or not self._current_device.control_url:
            return False
            
        try:
            # Generate DIDL-Lite metadata
            didl = self._generate_didl_metadata(uri, title) # Changed to _generate_didl_metadata
            import html
            metadata = html.escape(didl)
            safe_uri = html.escape(uri)
            
            return await self._send_soap_action(
                self._current_device.control_url,
                "SetNextAVTransportURI",
                f'''<u:SetNextAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
  <InstanceID>0</InstanceID>
  <NextURI>{safe_uri}</NextURI>
  <NextURIMetaData>{metadata}</NextURIMetaData>
</u:SetNextAVTransportURI>'''
            )
        except Exception:
            return False
    
    async def pause_stream(self) -> bool:
        """Pause the current stream."""
        if not self._current_device or not self._current_device.control_url:
            return False
            
        try:
            return await self._send_soap_action(
                self._current_device.control_url,
                "Pause",
                f'''<u:Pause xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Pause>'''
            )
        except Exception as e:
            print(f"Pause error: {e}")
            return False

    async def resume_stream(self) -> bool:
        """Resume the current stream."""
        if not self._current_device or not self._current_device.control_url:
            return False
            
        try:
            return await self._send_soap_action(
                self._current_device.control_url,
                "Play",
                f'''<u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>'''
            )
        except Exception as e:
            print(f"Resume error: {e}")
            return False

    async def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)."""
        if not self._current_device or not self._current_device.rendering_control_url:
            return False
            
        try:
            return await self._send_soap_action(
                self._current_device.rendering_control_url,
                "SetVolume",
                f'''<u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
  <InstanceID>0</InstanceID>
  <Channel>Master</Channel>
  <DesiredVolume>{volume}</DesiredVolume>
</u:SetVolume>'''
            )
        except Exception:
            return False

    async def set_mute(self, mute: bool) -> bool:
        """Set mute state."""
        if not self._current_device or not self._current_device.rendering_control_url:
            return False
            
        try:
            val = "1" if mute else "0"
            return await self._send_soap_action(
                self._current_device.rendering_control_url,
                "SetMute",
                f'''<u:SetMute xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
  <InstanceID>0</InstanceID>
  <Channel>Master</Channel>
  <DesiredMute>{val}</DesiredMute>
</u:SetMute>'''
            )
        except Exception:
            return False

    async def get_volume(self) -> int:
        """Get current volume (0-100)."""
        if not self._current_device or not self._current_device.rendering_control_url:
            return 0
            
        try:
            import re
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': '"urn:schemas-upnp-org:service:RenderingControl:1#GetVolume"',
            }
            
            body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:GetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
      <InstanceID>0</InstanceID>
      <Channel>Master</Channel>
    </u:GetVolume>
  </s:Body>
</s:Envelope>'''
            
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    self._current_device.rendering_control_url, 
                    content=body, 
                    headers=headers
                )
                
                if response.status_code == 200:
                    match = re.search(r'<CurrentVolume>(\d+)</CurrentVolume>', response.text)
                    if match:
                        return int(match.group(1))
            return 0
        except Exception:
            return 0

    async def _raw_upnp_stop(self) -> bool:
        """Stop playback using raw UPnP SOAP."""
        if not self._current_device or not self._current_device.control_url:
            # Try to fetch control URL if missing (rare case if device refetched)
             if self._current_device and not self._current_device.control_url:
                 # Attempt rediscovery/refetch logic here if needed, or fail
                 pass
             return False
        
        try:
            return await self._send_soap_action(
                self._current_device.control_url,
                "Stop",
                f'''<u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Stop>'''
            )
        except Exception:
            return False

    async def _send_soap_action(self, control_url: str, action: str, body_content: str) -> bool:
        """Send a raw SOAP action."""
        import httpx
        
        soap_body = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    {body_content}
  </s:Body>
</s:Envelope>'''
        
        headers = {
            'Content-Type': 'text/xml; charset="utf-8"',
            'SOAPAction': f'"urn:schemas-upnp-org:service:AVTransport:1#{action}"',
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(control_url, content=soap_body, headers=headers)
            return response.status_code == 200
    
    def get_current_device(self) -> Optional[DLNADevice]:
        """Get currently connected device."""
        return self._current_device
    
    def get_devices(self) -> List[DLNADevice]:
        """Get list of discovered devices."""
        return self._devices.copy()
    
    def get_current_device(self) -> Optional[DLNADevice]:
        """Get currently casting device."""
        return self._current_device
    
    def on_device_discovered(self, callback: Callable[[DLNADevice], None]):
        """Register callback for device discovery."""
        self._discovery_callbacks.append(callback)
