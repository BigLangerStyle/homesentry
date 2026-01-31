"""
Jellyfin monitoring module.

Collects app-specific metrics from Jellyfin Media Server via REST API.
Tracks streaming activity, transcoding sessions, and library size.

Configuration:
    JELLYFIN_API_URL: Jellyfin server URL (required)
    JELLYFIN_API_KEY: API key for authentication (required)
    JELLYFIN_TRANSCODE_COUNT_WARN: Warning threshold for transcode sessions
    JELLYFIN_TRANSCODE_COUNT_FAIL: Critical threshold for transcode sessions

Example:
    JELLYFIN_API_URL=http://192.168.1.8:8096
    JELLYFIN_API_KEY=1234567890abcdef1234567890abcdef
    JELLYFIN_TRANSCODE_COUNT_WARN=3
    JELLYFIN_TRANSCODE_COUNT_FAIL=5

Note:
    - Get API key from: Jellyfin Dashboard → API Keys → New API Key
    - API returns JSON responses (simpler than Plex XML)
    - Tracks both direct play and transcoding sessions
    - Works with Docker Jellyfin installations
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class JellyfinModule(AppModule):
    """Monitor Jellyfin Media Server."""
    
    # Module metadata
    APP_NAME = "jellyfin"
    APP_DISPLAY_NAME = "Jellyfin"
    CONTAINER_NAMES = ["jellyfin", "jellyfin-server"]
    
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from Jellyfin Media Server.
        
        Makes 2 API calls:
        1. GET /Sessions - Active streams and transcoding
        2. GET /Items/Counts - Library statistics
        
        Args:
            container: Docker container object
            config: Configuration dict with api_url, api_key
            
        Returns:
            Dict of metrics: active_streams, transcode_count, active_users,
                           library_items, movie_count, series_count, episode_count
        """
        api_url = config.get('api_url', '').rstrip('/')
        api_key = config.get('api_key', '')
        timeout = config.get('timeout', 10)
        
        if not api_url:
            logger.warning("Jellyfin module missing API URL")
            return {}
        
        if not api_key:
            logger.warning("Jellyfin module missing API key")
            return {}
        
        metrics = {}
        
        try:
            # Prepare headers with Jellyfin API key (uses Emby protocol)
            headers = {
                'X-Emby-Token': api_key,
                'Accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # API Call 1: Get active sessions (streams, transcodes, users)
                try:
                    async with session.get(
                        f"{api_url}/Sessions",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            sessions = await resp.json()
                            
                            # Count active streams (sessions with NowPlayingItem)
                            active_streams = 0
                            transcode_count = 0
                            active_users = set()
                            
                            for session in sessions:
                                # Check if session is actively playing something
                                now_playing = session.get('NowPlayingItem')
                                if now_playing:
                                    active_streams += 1
                                    
                                    # Track user
                                    username = session.get('UserName')
                                    if username:
                                        active_users.add(username)
                                    
                                    # Check if transcoding
                                    # TranscodingInfo exists and IsVideoDirect=false means transcoding
                                    transcode_info = session.get('TranscodingInfo')
                                    if transcode_info and transcode_info.get('IsVideoDirect') == False:
                                        transcode_count += 1
                            
                            metrics['active_streams'] = active_streams
                            metrics['transcode_count'] = transcode_count
                            metrics['active_users'] = len(active_users)
                            
                            logger.debug(
                                f"Jellyfin sessions: {active_streams} streams, "
                                f"{transcode_count} transcoding, "
                                f"{metrics['active_users']} users"
                            )
                        elif resp.status == 401:
                            logger.error("Jellyfin API key is invalid or expired")
                        else:
                            logger.warning(f"Failed to get Jellyfin sessions: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Jellyfin sessions request timed out after {timeout}s")
                except aiohttp.ClientError as e:
                    logger.error(f"Error getting Jellyfin sessions: {e}")
                except Exception as e:
                    logger.error(f"Error parsing Jellyfin sessions: {e}")
                
                # API Call 2: Get library statistics
                try:
                    async with session.get(
                        f"{api_url}/Items/Counts",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            counts = await resp.json()
                            
                            # Debug: log the type and content
                            logger.debug(f"Jellyfin counts type: {type(counts)}, value: {counts}")
                            
                            # Extract library counts (use bracket notation to avoid .get() issues)
                            movie_count = counts['MovieCount'] if 'MovieCount' in counts else 0
                            series_count = counts['SeriesCount'] if 'SeriesCount' in counts else 0
                            episode_count = counts['EpisodeCount'] if 'EpisodeCount' in counts else 0
                            
                            metrics['movie_count'] = movie_count
                            metrics['series_count'] = series_count
                            metrics['episode_count'] = episode_count
                            
                            # Calculate total items (movies + episodes)
                            metrics['library_items'] = movie_count + episode_count
                            
                            logger.debug(
                                f"Jellyfin library: {movie_count} movies, "
                                f"{series_count} series ({episode_count} episodes)"
                            )
                        elif resp.status == 401:
                            logger.error("Jellyfin API key is invalid or expired")
                        else:
                            logger.warning(f"Failed to get Jellyfin library counts: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Jellyfin library request timed out after {timeout}s")
                except aiohttp.ClientError as e:
                    logger.error(f"Error getting Jellyfin library counts: {e}")
                except Exception as e:
                    logger.error(f"Error parsing Jellyfin library counts: {e}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error collecting Jellyfin metrics: {e}", exc_info=True)
            return {}
    
    def determine_status(self, metrics: Dict[str, Any], config: dict) -> str:
        """
        Determine Jellyfin status based on metrics.
        
        Status logic:
        - FAIL: No metrics collected (API unreachable)
        - WARN: High transcode count (CPU intensive)
        - OK: Normal operation
        
        Args:
            metrics: Collected metrics dict
            config: Configuration with thresholds
            
        Returns:
            Status string: 'OK', 'WARN', or 'FAIL'
        """
        # If no metrics collected, API is likely down
        if not metrics:
            return 'FAIL'
        
        # Check transcode count thresholds
        transcode_count = metrics.get('transcode_count', 0)
        transcode_warn = config.get('transcode_count_warn', 3)
        transcode_fail = config.get('transcode_count_fail', 5)
        
        if transcode_count >= transcode_fail:
            return 'FAIL'
        elif transcode_count >= transcode_warn:
            return 'WARN'
        
        return 'OK'
    
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """
        Validate Jellyfin configuration.
        
        Args:
            config: Configuration dict to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'api_url' not in config or not config['api_url']:
            return (False, "api_url is required")
        
        if not config['api_url'].startswith('http'):
            return (False, "api_url must start with http:// or https://")
        
        if 'api_key' not in config or not config['api_key']:
            return (False, "api_key is required (generate in Jellyfin Dashboard → API Keys)")
        
        return (True, "")
