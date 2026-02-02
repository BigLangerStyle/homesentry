"""
Base class for all application-specific monitoring modules.

This provides the interface that all modules must implement.
Keep it simple - modules should only need 2-3 methods.

Example Module Template:

    from app.collectors.modules.base import AppModule
    import aiohttp
    import logging

    logger = logging.getLogger(__name__)

    class ExampleAppModule(AppModule):
        '''Monitor Example App container.'''
        
        # Module metadata
        APP_NAME = "exampleapp"
        APP_DISPLAY_NAME = "Example App"
        CONTAINER_NAMES = ["exampleapp", "example-app"]
        CARD_METRICS = ["total_items", "active_users", "queue_size"]
        
        async def collect(self, container, config: dict) -> dict:
            '''
            Collect metrics from Example App.
            
            This example shows:
            - Reading config
            - Making an API call
            - Parsing response
            - Returning metrics
            '''
            # Get configuration
            api_url = config.get('api_url', 'http://exampleapp:8080')
            timeout = config.get('timeout', 10)
            
            try:
                # Make API call (count toward 3-call limit)
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{api_url}/api/status",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"API returned {resp.status}")
                            return {}
                        
                        data = await resp.json()
                
                # Extract metrics
                metrics = {
                    'total_items': data.get('total_items', 0),
                    'active_users': data.get('active_users', 0),
                    'queue_size': data.get('queue_size', 0)
                }
                
                return metrics
                
            except aiohttp.ClientError as e:
                logger.error(f"Failed to collect from Example App: {e}")
                return {}
            except Exception as e:
                logger.error(f"Unexpected error in Example App module: {e}")
                return {}
        
        def validate_config(self, config: dict) -> tuple[bool, str]:
            '''Validate configuration.'''
            if 'api_url' not in config:
                return (False, "api_url is required")
            
            if not config['api_url'].startswith('http'):
                return (False, "api_url must start with http:// or https://")
            
            return (True, "")
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple


class AppModule(ABC):
    """
    Abstract base class for app-specific monitoring modules.
    
    Modules inherit this class and implement collect() to provide
    app-specific metrics beyond generic Docker container monitoring.
    
    Example:
        class HomeAssistantModule(AppModule):
            APP_NAME = "homeassistant"
            APP_DISPLAY_NAME = "Home Assistant"
            CONTAINER_NAMES = ["homeassistant", "hass"]
            
            async def collect(self, container, config: dict) -> dict:
                # Make API call
                states = await self.api_get(f"{config['api_url']}/api/states")
                return {'entity_count': len(states)}
    """
    
    # Module metadata (must be overridden by subclass)
    APP_NAME: str = ""              # Used for config keys (lowercase)
    APP_DISPLAY_NAME: str = ""      # Used in UI (friendly name)
    CONTAINER_NAMES: List[str] = [] # Container names this module handles
    CARD_METRICS: List[str] = []    # Metric names to show on dashboard card (priority order)
    
    # Hard limits (enforced by framework)
    MAX_METRICS = 10
    MAX_API_CALLS = 3
    MAX_CONFIG_OPTIONS = 15
    
    @classmethod
    def detect(cls, container) -> bool:
        """
        Check if this module applies to a container.
        
        Default implementation checks if container name matches CONTAINER_NAMES.
        Override for custom detection logic.
        
        Args:
            container: Docker container object
            
        Returns:
            True if module should monitor this container
        """
        return container.name in cls.CONTAINER_NAMES
    
    @abstractmethod
    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect app-specific metrics for this container.
        
        This is the main method modules implement. It should:
        1. Make API calls (max 3) to the application
        2. Parse responses and extract metrics
        3. Return dict of {metric_name: value}
        
        The framework handles:
        - Database storage
        - Alert processing
        - Error recovery
        - Rate limiting
        
        Args:
            container: Docker container object
            config: Configuration dict from environment variables
            
        Returns:
            Dict of {metric_name: value}
            - Keys: Metric names (lowercase, underscores)
            - Values: Numeric values (int/float) or status strings
            
        Example:
            return {
                'entity_count': 342,
                'automation_count': 45,
                'database_size_mb': 3247.8
            }
        """
        pass
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """
        Validate module configuration.
        
        Override to add custom validation logic.
        Return (True, "") if valid, (False, "error message") if invalid.
        
        Args:
            config: Configuration dict
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return (True, "")
