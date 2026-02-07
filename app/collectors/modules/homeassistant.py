"""
Home Assistant monitoring module.

Collects app-specific metrics from Home Assistant via REST API.
Tracks entity count, automation count, and system health.

Configuration:
    HOMEASSISTANT_API_URL: Home Assistant API endpoint (required)
    HOMEASSISTANT_API_TOKEN: Long-lived access token (required)
    HOMEASSISTANT_ENTITY_COUNT_WARN: Warning threshold for entity count
    HOMEASSISTANT_ENTITY_COUNT_FAIL: Critical threshold for entity count
    HOMEASSISTANT_AUTOMATION_COUNT_WARN: Warning threshold for automation count
    HOMEASSISTANT_AUTOMATION_COUNT_FAIL: Critical threshold for automation count

Example:
    HOMEASSISTANT_API_URL=http://homeassistant:8123
    HOMEASSISTANT_API_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...
    HOMEASSISTANT_ENTITY_COUNT_WARN=500
    HOMEASSISTANT_ENTITY_COUNT_FAIL=1000
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HomeAssistantModule(AppModule):
    """Monitor Home Assistant container."""
    
    # Module metadata
    APP_NAME = "homeassistant"
    APP_DISPLAY_NAME = "Home Assistant"
    CONTAINER_NAMES = ["homeassistant", "hass"]
    
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from Home Assistant.
        
        Makes up to 2 API calls:
        1. GET /api/states - For entity and automation counts
        2. GET /api/ - For API health and response time
        
        Args:
            container: Docker container object
            config: Configuration dict with api_url, api_token
            
        Returns:
            Dict of metrics: entity_count, automation_count, response_time_ms
        """
        api_url = config.get('api_url', '').rstrip('/')
        api_token = config.get('api_token', '')
        timeout = config.get('timeout', 10)
        
        if not api_url or not api_token:
            logger.warning(
                f"Home Assistant module missing required config "
                f"(api_url: {bool(api_url)}, api_token: {bool(api_token)})"
            )
            return {}
        
        metrics = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare headers with Bearer token
                headers = {
                    'Authorization': f'Bearer {api_token}',
                    'Content-Type': 'application/json'
                }
                
                # API Call 1: Get all states (for entity and automation counts)
                try:
                    start_time = time.time()
                    
                    async with session.get(
                        f"{api_url}/api/states",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        ssl=False  # Accept self-signed certificates
                    ) as resp:
                        response_time_ms = (time.time() - start_time) * 1000
                        
                        if resp.status == 401:
                            logger.error("Home Assistant authentication failed (401 Unauthorized)")
                            return {}
                        
                        if resp.status == 403:
                            logger.error("Home Assistant access forbidden (403 Forbidden)")
                            return {}
                        
                        if resp.status != 200:
                            logger.warning(f"Home Assistant API returned HTTP {resp.status}")
                            return {}
                        
                        states = await resp.json()
                        
                        # Extract metrics
                        metrics['entity_count'] = len(states)
                        
                        # Count automations (entities starting with "automation.")
                        automation_count = sum(
                            1 for state in states 
                            if state.get('entity_id', '').startswith('automation.')
                        )
                        metrics['automation_count'] = automation_count
                        
                        # Response time (already measured above)
                        metrics['response_time_ms'] = round(response_time_ms, 2)
                        
                        logger.info(
                            f"Home Assistant metrics: {metrics['entity_count']} entities, "
                            f"{automation_count} automations, {response_time_ms:.0f}ms response"
                        )
                
                except asyncio.TimeoutError:
                    logger.warning(f"Home Assistant API request timed out after {timeout}s")
                    return {}
                
                except aiohttp.ClientError as e:
                    logger.error(f"Home Assistant API connection error: {e}")
                    return {}
        
        except Exception as e:
            logger.error(f"Unexpected error in Home Assistant module: {e}", exc_info=True)
            return {}
        
        return metrics
    
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """
        Validate Home Assistant configuration.
        
        Checks:
        - api_url is present and valid format
        - api_token is present
        
        Args:
            config: Configuration dict
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check api_url
        if 'api_url' not in config:
            return (False, "api_url is required")
        
        api_url = config['api_url']
        if not api_url.startswith('http://') and not api_url.startswith('https://'):
            return (False, "api_url must start with http:// or https://")
        
        # Check api_token
        if 'api_token' not in config:
            return (False, "api_token is required")
        
        api_token = config['api_token']
        if not api_token or len(api_token) < 10:
            return (False, "api_token appears invalid (too short)")
        
        return (True, "")
