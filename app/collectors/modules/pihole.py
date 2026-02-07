"""
Pi-hole monitoring module.

Collects app-specific metrics from Pi-hole via Admin API.
Tracks DNS blocking effectiveness and network activity.

Configuration:
    PIHOLE_API_URL: Pi-hole Admin API URL (required)
    PIHOLE_API_PASSWORD: App password for authentication (required for Pi-hole v6+)
    PIHOLE_BARE_METAL: Set to 'true' for bare-metal installations (default: false)
    PIHOLE_BLOCKED_PERCENT_WARN: Warning threshold for block percentage (default: 10)
    PIHOLE_BLOCKED_PERCENT_FAIL: Critical threshold for block percentage (default: 5)
    PIHOLE_ACTIVE_CLIENTS_WARN: Warning threshold for active clients (optional)

Example:
    PIHOLE_API_URL=http://192.168.1.8:80
    PIHOLE_API_PASSWORD=your_app_password_here
    PIHOLE_BARE_METAL=true
    PIHOLE_BLOCKED_PERCENT_WARN=10
    PIHOLE_BLOCKED_PERCENT_FAIL=5

Note:
    - Pi-hole v6+ requires app password authentication
    - Get app password from: Pi-hole web UI → Settings → API → Configure app password
    - Uses session-based authentication (login → get sid/csrf → use for API calls)
    - Works with both containerized and bare-metal Pi-hole installations
    - For bare-metal Pi-hole, set PIHOLE_BARE_METAL=true
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PiHoleModule(AppModule):
    """Monitor Pi-hole DNS sinkhole."""
    
    # Module metadata
    APP_NAME = "pihole"
    APP_DISPLAY_NAME = "Pi-hole"
    CONTAINER_NAMES = ["pihole", "pi-hole"]
    
    def __init__(self):
        """Initialize module with session cache."""
        self._session_sid = None
        self._session_csrf = None
    
    async def _authenticate(
        self,
        session: aiohttp.ClientSession,
        api_url: str,
        password: str,
        timeout: int
    ) -> bool:
        """
        Authenticate with Pi-hole v6 API to get session cookie and CSRF token.
        
        Args:
            session: aiohttp session
            api_url: Base API URL
            password: App password from Pi-hole web UI
            timeout: Request timeout in seconds
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            async with session.post(
                f"{api_url}/api/auth",
                json={"password": password},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    session_data = data.get('session', {})
                    
                    if session_data.get('valid'):
                        self._session_sid = session_data.get('sid')
                        self._session_csrf = session_data.get('csrf')
                        
                        logger.debug(
                            f"Pi-hole authentication successful "
                            f"(session valid for {session_data.get('validity', 0)}s)"
                        )
                        return True
                    else:
                        logger.warning(f"Pi-hole authentication failed: invalid session")
                        return False
                else:
                    logger.warning(f"Pi-hole authentication failed: HTTP {resp.status}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.warning(f"Pi-hole authentication timed out after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Pi-hole authentication error: {e}")
            return False
    
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from Pi-hole.
        
        Authentication flow:
        1. POST /api/auth with app password
        2. Extract sid cookie and csrf token
        3. GET /api/stats/summary with Cookie: sid and X-CSRF-Token headers
        
        Args:
            container: Docker container object (or None for bare-metal)
            config: Configuration dict with api_url and api_password
            
        Returns:
            Dict of metrics: queries_blocked_today, total_queries_today, 
                           percent_blocked, active_clients, blocklist_size,
                           queries_forwarded
        """
        api_url = config.get('api_url', '').rstrip('/')
        api_password = config.get('api_password', '')
        timeout = config.get('timeout', 10)
        
        if not api_url:
            logger.warning("Pi-hole module missing API URL")
            return {}
        
        if not api_password:
            logger.warning("Pi-hole module missing API password")
            return {}
        
        metrics = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Authenticate to get session cookie and CSRF token
                auth_success = await self._authenticate(session, api_url, api_password, timeout)
                
                if not auth_success:
                    logger.error("Failed to authenticate with Pi-hole")
                    return {}
                
                # Get stats using session credentials
                try:
                    headers = {
                        'Cookie': f'sid={self._session_sid}',
                        'X-CSRF-Token': self._session_csrf
                    }
                    
                    async with session.get(
                        f"{api_url}/api/stats/summary",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            # Extract metrics from v6 API response
                            queries = data.get('queries', {})
                            clients = data.get('clients', {})
                            gravity = data.get('gravity', {})
                            
                            # Total queries today
                            metrics['total_queries_today'] = queries.get('total', 0)
                            
                            # Queries blocked today
                            metrics['queries_blocked_today'] = queries.get('blocked', 0)
                            
                            # Block percentage
                            metrics['percent_blocked'] = round(queries.get('percent_blocked', 0.0), 1)
                            
                            # Active clients
                            metrics['active_clients'] = clients.get('active', 0)
                            
                            # Blocklist size (domains being blocked)
                            metrics['blocklist_size'] = gravity.get('domains_being_blocked', 0)
                            
                            # Queries forwarded (to upstream DNS)
                            status_counts = queries.get('status', {})
                            metrics['queries_forwarded'] = status_counts.get('FORWARDED', 0)
                            
                            logger.info(
                                f"Pi-hole stats: "
                                f"{metrics['queries_blocked_today']:,} blocked "
                                f"({metrics['percent_blocked']}%), "
                                f"{metrics['active_clients']} clients"
                            )
                            
                            return metrics
                        else:
                            logger.warning(f"Failed to get Pi-hole stats: HTTP {resp.status}")
                            return {}
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Pi-hole stats request timed out after {timeout}s")
                    return {}
                except aiohttp.ClientError as e:
                    logger.error(f"Error getting Pi-hole stats: {e}")
                    return {}
                except Exception as e:
                    logger.error(f"Unexpected error getting Pi-hole stats: {e}")
                    return {}
                
        except Exception as e:
            logger.error(f"Error collecting Pi-hole metrics: {e}", exc_info=True)
            return {}
    
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """
        Validate Pi-hole configuration.
        
        Checks:
        - api_url is present and valid format
        - api_password is present
        
        Args:
            config: Configuration dict
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'api_url' not in config or not config['api_url']:
            return (False, "api_url is required")
        
        api_url = config['api_url']
        if not api_url.startswith('http://') and not api_url.startswith('https://'):
            return (False, "api_url must start with http:// or https://")
        
        if 'api_password' not in config or not config['api_password']:
            return (False, "api_password is required (get from Pi-hole web UI → Settings → API → Configure app password)")
        
        return (True, "")
