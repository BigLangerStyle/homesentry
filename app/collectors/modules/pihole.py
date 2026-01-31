"""
Pi-hole monitoring module.

Collects app-specific metrics from Pi-hole via Admin API.
Tracks DNS blocking effectiveness and network activity.

Configuration:
    PIHOLE_API_URL: Pi-hole Admin API URL (required)
    PIHOLE_BLOCKED_PERCENT_WARN: Warning threshold for block percentage (default: 10)
    PIHOLE_BLOCKED_PERCENT_FAIL: Critical threshold for block percentage (default: 5)
    PIHOLE_ACTIVE_CLIENTS_WARN: Warning threshold for active clients (optional)

Example:
    PIHOLE_API_URL=http://192.168.1.8:80
    PIHOLE_BLOCKED_PERCENT_WARN=10
    PIHOLE_BLOCKED_PERCENT_FAIL=5

Note:
    Pi-hole API requires no authentication for summary stats.
    Works with both containerized and bare-metal Pi-hole installations.
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class PiHoleModule(AppModule):
    """Monitor Pi-hole DNS sinkhole."""
    
    # Module metadata
    APP_NAME = "pihole"
    APP_DISPLAY_NAME = "Pi-hole"
    CONTAINER_NAMES = ["pihole", "pi-hole"]
    
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from Pi-hole.
        
        Makes 1 API call:
        1. GET /admin/api.php?summaryRaw - All stats in one request
        
        Args:
            container: Docker container object (or None for bare-metal)
            config: Configuration dict with api_url
            
        Returns:
            Dict of metrics: queries_blocked_today, total_queries_today, 
                           percent_blocked, active_clients, blocklist_size,
                           queries_forwarded
        """
        api_url = config.get('api_url', '').rstrip('/')
        timeout = config.get('timeout', 10)
        
        if not api_url:
            logger.warning("Pi-hole module missing API URL")
            return {}
        
        metrics = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # API Call: Get summary stats (everything in one call!)
                try:
                    async with session.get(
                        f"{api_url}/admin/api.php?summaryRaw",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            # Queries blocked today
                            metrics['queries_blocked_today'] = int(data.get('ads_blocked_today', 0))
                            
                            # Total queries today
                            metrics['total_queries_today'] = int(data.get('dns_queries_today', 0))
                            
                            # Block percentage
                            percent_str = data.get('ads_percentage_today', '0')
                            try:
                                metrics['percent_blocked'] = float(percent_str)
                            except (ValueError, TypeError):
                                metrics['percent_blocked'] = 0.0
                            
                            # Active clients
                            metrics['active_clients'] = int(data.get('unique_clients', 0))
                            
                            # Blocklist size (total blocked domains)
                            blocklist_str = data.get('domains_being_blocked', '0')
                            # Handle both string and int formats
                            try:
                                # Remove commas if present (Pi-hole sometimes formats large numbers)
                                if isinstance(blocklist_str, str):
                                    metrics['blocklist_size'] = int(blocklist_str.replace(',', ''))
                                else:
                                    metrics['blocklist_size'] = int(blocklist_str)
                            except (ValueError, AttributeError):
                                metrics['blocklist_size'] = 0
                            
                            # Queries forwarded (to upstream DNS)
                            metrics['queries_forwarded'] = int(data.get('queries_forwarded', 0))
                            
                            logger.info(
                                f"Pi-hole stats: "
                                f"{metrics['queries_blocked_today']:,} blocked "
                                f"({metrics['percent_blocked']}%), "
                                f"{metrics['active_clients']} clients"
                            )
                        else:
                            logger.warning(f"Failed to get Pi-hole stats: HTTP {resp.status}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Pi-hole API request timed out after {timeout}s")
                except aiohttp.ClientError as e:
                    logger.error(f"Error getting Pi-hole stats: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error getting Pi-hole stats: {e}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error collecting Pi-hole metrics: {e}", exc_info=True)
            return {}
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """
        Validate Pi-hole configuration.
        
        Checks:
        - api_url is present and valid format
        
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
        
        return (True, "")
