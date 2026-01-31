"""
qBittorrent monitoring module.

Collects app-specific metrics from qBittorrent via Web API.
Tracks torrent activity, bandwidth usage, and disk space (if available).

Configuration:
    QBITTORRENT_API_URL: qBittorrent Web UI URL (required)
    QBITTORRENT_USERNAME: Web UI username (default: admin)
    QBITTORRENT_PASSWORD: Web UI password (required)
    QBITTORRENT_ACTIVE_TORRENTS_WARN: Warning threshold for active torrents
    QBITTORRENT_ACTIVE_TORRENTS_FAIL: Critical threshold for active torrents
    QBITTORRENT_DISK_FREE_WARN_GB: Warning threshold for free disk space (GB)
    QBITTORRENT_DISK_FREE_FAIL_GB: Critical threshold for free disk space (GB)

Note:
    The disk_free_gb metric is only collected if your qBittorrent version
    provides the 'free_space_on_disk' field in the API response.
    Older versions may not include this field.

Example:
    QBITTORRENT_API_URL=http://qbittorrent:8080
    QBITTORRENT_USERNAME=admin
    QBITTORRENT_PASSWORD=mypassword
    QBITTORRENT_ACTIVE_TORRENTS_WARN=10
    QBITTORRENT_DISK_FREE_WARN_GB=100
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class QBittorrentModule(AppModule):
    """Monitor qBittorrent container."""
    
    # Module metadata
    APP_NAME = "qbittorrent"
    APP_DISPLAY_NAME = "qBittorrent"
    CONTAINER_NAMES = ["qbittorrent", "qbittorrent-vpn", "qbittorrentvpn"]
    
    def __init__(self):
        """Initialize module with session cookie storage."""
        self._session_cookie = None
    
    async def _authenticate(self, session: aiohttp.ClientSession, api_url: str, username: str, password: str) -> bool:
        """
        Authenticate with qBittorrent Web UI.
        
        Args:
            session: aiohttp session
            api_url: Base API URL
            username: Username
            password: Password
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Login endpoint
            login_url = f"{api_url}/api/v2/auth/login"
            
            # Send login request
            async with session.post(
                login_url,
                data={'username': username, 'password': password},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    # Check response text - "Ok." means success, "Fails." means auth failed
                    response_text = await resp.text()
                    if response_text.strip() == "Ok.":
                        # Store session cookie for subsequent requests
                        self._session_cookie = resp.cookies.get('SID')
                        logger.debug("qBittorrent authentication successful")
                        return True
                    else:
                        logger.warning(f"qBittorrent authentication failed: {response_text}")
                        return False
                else:
                    logger.warning(f"qBittorrent authentication failed: HTTP {resp.status}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("qBittorrent authentication timed out")
            return False
        except Exception as e:
            logger.error(f"qBittorrent authentication error: {e}")
            return False
    
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from qBittorrent.
        
        Makes up to 2 API calls:
        1. GET /api/v2/transfer/info - For speeds and disk space
        2. GET /api/v2/torrents/info - For active torrent count
        
        Args:
            container: Docker container object
            config: Configuration dict with api_url, username, password
            
        Returns:
            Dict of metrics: active_torrents, download_speed_mbps, upload_speed_mbps, 
                           session_downloaded_gb, session_uploaded_gb
                           Optional: disk_free_gb (only if API provides it)
        """
        api_url = config.get('api_url', '').rstrip('/')
        username = config.get('username', 'admin')
        password = config.get('password', '')
        timeout = config.get('timeout', 10)
        
        if not api_url:
            logger.warning(
                "qBittorrent module missing API URL"
            )
            return {}
        
        if not password:
            logger.warning(
                "qBittorrent module missing password"
            )
            return {}
        
        metrics = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Authenticate first
                auth_success = await self._authenticate(session, api_url, username, password)
                
                if not auth_success:
                    logger.error("Failed to authenticate with qBittorrent")
                    return {}
                
                # Prepare headers with session cookie
                cookies = {'SID': self._session_cookie.value} if self._session_cookie else {}
                
                # API Call 1: Get transfer info (speeds, disk space, session stats)
                try:
                    async with session.get(
                        f"{api_url}/api/v2/transfer/info",
                        cookies=cookies,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            transfer_data = await resp.json()
                            
                            # Download speed (bytes/sec -> Mbps)
                            dl_speed_bytes = transfer_data.get('dl_info_speed', 0)
                            metrics['download_speed_mbps'] = round(dl_speed_bytes * 8 / 1_000_000, 2)
                            
                            # Upload speed (bytes/sec -> Mbps)
                            up_speed_bytes = transfer_data.get('up_info_speed', 0)
                            metrics['upload_speed_mbps'] = round(up_speed_bytes * 8 / 1_000_000, 2)
                            
                            # Free disk space (bytes -> GB) - only if available
                            # Some qBittorrent versions don't provide this field
                            if 'free_space_on_disk' in transfer_data:
                                free_bytes = transfer_data['free_space_on_disk']
                                if free_bytes > 0:  # Only include if value is meaningful
                                    metrics['disk_free_gb'] = round(free_bytes / 1_073_741_824, 2)
                            
                            # Session downloaded (bytes -> GB)
                            dl_bytes = transfer_data.get('dl_info_data', 0)
                            metrics['session_downloaded_gb'] = round(dl_bytes / 1_073_741_824, 2)
                            
                            # Session uploaded (bytes -> GB)
                            up_bytes = transfer_data.get('up_info_data', 0)
                            metrics['session_uploaded_gb'] = round(up_bytes / 1_073_741_824, 2)
                            
                            # Build log message
                            log_parts = [
                                f"DL {metrics['download_speed_mbps']} Mbps",
                                f"UL {metrics['upload_speed_mbps']} Mbps"
                            ]
                            if 'disk_free_gb' in metrics:
                                log_parts.append(f"{metrics['disk_free_gb']} GB free")
                            
                            logger.debug(f"qBittorrent transfer info: {', '.join(log_parts)}")
                        else:
                            logger.warning(f"Failed to get qBittorrent transfer info: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"qBittorrent transfer info request timed out after {timeout}s")
                except aiohttp.ClientError as e:
                    logger.error(f"Error getting qBittorrent transfer info: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error getting qBittorrent transfer info: {e}")
                
                # API Call 2: Get active torrent count
                try:
                    async with session.get(
                        f"{api_url}/api/v2/torrents/info",
                        cookies=cookies,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            torrents = await resp.json()
                            
                            # Count active torrents (downloading or seeding)
                            # Active states include: downloading, uploading, stalledDL, stalledUP, 
                            # checkingDL, checkingUP, queuedDL, queuedUP, metaDL
                            active_states = [
                                'downloading', 'uploading', 'stalledDL', 'stalledUP', 
                                'checkingDL', 'checkingUP', 'queuedDL', 'queuedUP',
                                'metaDL'
                            ]
                            active_count = sum(1 for t in torrents if t.get('state') in active_states)
                            
                            metrics['active_torrents'] = active_count
                            
                            logger.info(
                                f"qBittorrent metrics: {active_count} active torrents, "
                                f"DL {metrics.get('download_speed_mbps', 0)} Mbps, "
                                f"UL {metrics.get('upload_speed_mbps', 0)} Mbps"
                            )
                        else:
                            logger.warning(f"Failed to get qBittorrent torrents: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"qBittorrent torrents request timed out after {timeout}s")
                except aiohttp.ClientError as e:
                    logger.error(f"Error getting qBittorrent torrents: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error getting qBittorrent torrents: {e}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error collecting qBittorrent metrics: {e}", exc_info=True)
            return {}
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """
        Validate qBittorrent configuration.
        
        Checks:
        - api_url is present and valid format
        - password is present
        
        Args:
            config: Configuration dict
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check api_url
        if 'api_url' not in config or not config['api_url']:
            return (False, "api_url is required")
        
        api_url = config['api_url']
        if not api_url.startswith('http://') and not api_url.startswith('https://'):
            return (False, "api_url must start with http:// or https://")
        
        # Check password
        if 'password' not in config or not config['password']:
            return (False, "password is required for qBittorrent authentication")
        
        return (True, "")
