"""
Plex Media Server monitoring module.

Collects app-specific metrics from Plex Media Server via API.
Tracks streaming activity, transcoding sessions, and library size.

Configuration:
    PLEX_API_URL: Plex Media Server URL (required)
    PLEX_API_TOKEN: X-Plex-Token for authentication (required)
    PLEX_BARE_METAL: Set to 'true' for bare-metal installations (default: false)
    PLEX_TRANSCODE_COUNT_WARN: Warning threshold for transcode sessions
    PLEX_TRANSCODE_COUNT_FAIL: Critical threshold for transcode sessions

Example:
    PLEX_API_URL=http://192.168.1.8:32400
    PLEX_API_TOKEN=aBcDeFgHiJkLmNoPqRsTuV
    PLEX_BARE_METAL=true
    PLEX_TRANSCODE_COUNT_WARN=3
    PLEX_TRANSCODE_COUNT_FAIL=5

Note:
    - Get X-Plex-Token from: Plex Web → Account Settings → Show (under Plex Token)
    - For bare-metal Plex (systemd), set PLEX_BARE_METAL=true
    - API returns XML responses (not JSON)
    - Tracks both direct play and transcoding sessions
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class PlexModule(AppModule):
    """Monitor Plex Media Server."""
    
    # Module metadata
    APP_NAME = "plex"
    APP_DISPLAY_NAME = "Plex Media Server"
    CONTAINER_NAMES = ["plex", "plexmediaserver"]
    
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from Plex Media Server.
        
        Makes up to 3 API calls:
        1. GET /status/sessions - Active streams and transcoding
        2. GET /library/sections - Library structure
        3. GET /library/sections/{id}/all - Per-section counts (for each library)
        
        Args:
            container: Docker container object (or None for bare-metal)
            config: Configuration dict with api_url, api_token
            
        Returns:
            Dict of metrics: active_streams, transcode_count, library_items,
                           movie_count, tv_show_count, bandwidth_mbps
        """
        api_url = config.get('api_url', '').rstrip('/')
        api_token = config.get('api_token', '')
        timeout = config.get('timeout', 10)
        
        if not api_url:
            logger.warning("Plex module missing API URL")
            return {}
        
        if not api_token:
            logger.warning("Plex module missing API token")
            return {}
        
        metrics = {}
        
        try:
            # Prepare headers with Plex token
            headers = {
                'X-Plex-Token': api_token,
                'Accept': 'application/xml'
            }
            
            async with aiohttp.ClientSession() as session:
                # API Call 1: Get active sessions (streams, transcodes, bandwidth)
                try:
                    async with session.get(
                        f"{api_url}/status/sessions",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            xml_data = await resp.text()
                            root = ET.fromstring(xml_data)
                            
                            # Active streams count
                            active_streams = int(root.get('size', 0))
                            metrics['active_streams'] = active_streams
                            
                            # Count transcode sessions and calculate bandwidth
                            transcode_count = 0
                            total_bandwidth_kbps = 0
                            
                            for video in root.findall('.//Video'):
                                # Check if transcoding
                                transcode_session = video.find('TranscodeSession')
                                if transcode_session is not None:
                                    transcode_count += 1
                                
                                # Get bandwidth (in Kbps)
                                media = video.find('.//Media')
                                if media is not None:
                                    bitrate = int(media.get('bitrate', 0))
                                    total_bandwidth_kbps += bitrate
                            
                            metrics['transcode_count'] = transcode_count
                            
                            # Convert bandwidth to Mbps
                            metrics['bandwidth_mbps'] = round(total_bandwidth_kbps / 1000, 2)
                            
                            logger.debug(
                                f"Plex sessions: {active_streams} streams, "
                                f"{transcode_count} transcoding, "
                                f"{metrics['bandwidth_mbps']} Mbps"
                            )
                        else:
                            logger.warning(f"Failed to get Plex sessions: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Plex sessions request timed out after {timeout}s")
                except ET.ParseError as e:
                    logger.error(f"Failed to parse Plex XML response: {e}")
                except Exception as e:
                    logger.error(f"Error getting Plex sessions: {e}")
                
                # API Call 2: Get library statistics
                try:
                    async with session.get(
                        f"{api_url}/library/sections",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            xml_data = await resp.text()
                            root = ET.fromstring(xml_data)
                            
                            # Count items by library type
                            movie_count = 0
                            tv_show_count = 0
                            music_count = 0
                            
                            for directory in root.findall('.//Directory'):
                                lib_type = directory.get('type', '')
                                
                                # Get section ID to query for count
                                section_id = directory.get('key', '')
                                
                                if section_id:
                                    try:
                                        # API Call 3: Quick count query (no items returned, just count)
                                        async with session.get(
                                            f"{api_url}/library/sections/{section_id}/all",
                                            headers=headers,
                                            params={'X-Plex-Container-Size': '0'},
                                            timeout=aiohttp.ClientTimeout(total=timeout)
                                        ) as count_resp:
                                            if count_resp.status == 200:
                                                count_xml = await count_resp.text()
                                                count_root = ET.fromstring(count_xml)
                                                total_size = int(count_root.get('totalSize', 0))
                                                
                                                if lib_type == 'movie':
                                                    movie_count += total_size
                                                elif lib_type == 'show':
                                                    tv_show_count += total_size
                                                elif lib_type == 'artist':
                                                    music_count += total_size
                                    except Exception as e:
                                        logger.debug(f"Could not get count for section {section_id}: {e}")
                            
                            metrics['movie_count'] = movie_count
                            metrics['tv_show_count'] = tv_show_count
                            metrics['library_items'] = movie_count + tv_show_count + music_count
                            
                            logger.debug(
                                f"Plex library: {movie_count} movies, "
                                f"{tv_show_count} shows, "
                                f"{metrics['library_items']} total"
                            )
                        else:
                            logger.warning(f"Failed to get Plex library stats: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Plex library request timed out after {timeout}s")
                except ET.ParseError as e:
                    logger.error(f"Failed to parse Plex library XML: {e}")
                except Exception as e:
                    logger.error(f"Error getting Plex library stats: {e}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error collecting Plex metrics: {e}", exc_info=True)
            return {}
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """
        Validate Plex configuration.
        
        Checks:
        - api_url is present and valid format
        - api_token is present
        
        Args:
            config: Configuration dict
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'api_url' not in config or not config['api_url']:
            return (False, "api_url is required")
        
        if not config['api_url'].startswith('http://') and not config['api_url'].startswith('https://'):
            return (False, "api_url must start with http:// or https://")
        
        if 'api_token' not in config or not config['api_token']:
            return (False, "api_token is required (X-Plex-Token from Plex Web UI)")
        
        return (True, "")
