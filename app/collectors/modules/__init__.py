"""
App Module System for HomeSentry

Provides automatic discovery and loading of application-specific monitoring modules.
Modules are Python files in this directory that define classes inheriting from AppModule.
"""

import os
import logging
import importlib
import inspect
from pathlib import Path
from typing import List, Type, Dict, Any

from .base import AppModule

logger = logging.getLogger(__name__)


def discover_available_modules() -> List[Type[AppModule]]:
    """
    Scan modules/ directory and return all AppModule subclasses.
    
    This enables:
    - Automatic module loading at runtime
    - Future install UI to enumerate available modules
    - Community modules (just drop file in directory)
    
    Returns:
        List of AppModule class objects (not instances)
    """
    modules = []
    
    # Get the directory where this file lives
    modules_dir = Path(__file__).parent
    
    # Scan for Python files in this directory
    for file_path in modules_dir.glob("*.py"):
        # Skip __init__.py, base.py, and private files (starting with _)
        if file_path.name in ("__init__.py", "base.py") or file_path.name.startswith("_"):
            continue
        
        try:
            # Import the module
            module_name = f"app.collectors.modules.{file_path.stem}"
            module = importlib.import_module(module_name)
            
            # Find all classes in the module that inherit from AppModule
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a subclass of AppModule (but not AppModule itself)
                if issubclass(obj, AppModule) and obj is not AppModule:
                    # Validate that the module has required attributes
                    if not obj.APP_NAME:
                        logger.warning(
                            f"Module {name} in {file_path.name} has no APP_NAME, skipping"
                        )
                        continue
                    
                    if not obj.CONTAINER_NAMES:
                        logger.warning(
                            f"Module {name} in {file_path.name} has no CONTAINER_NAMES, skipping"
                        )
                        continue
                    
                    modules.append(obj)
                    logger.info(
                        f"Discovered module: {obj.APP_DISPLAY_NAME or obj.APP_NAME} "
                        f"(containers: {', '.join(obj.CONTAINER_NAMES)})"
                    )
        
        except Exception as e:
            logger.error(
                f"Failed to import module from {file_path.name}: {e}",
                exc_info=True
            )
    
    logger.info(f"Discovered {len(modules)} app module(s)")
    return modules


def load_module_config(app_name: str) -> Dict[str, Any]:
    """
    Load configuration for a specific module from environment variables.
    
    Convention: {APP_NAME}_{SETTING_NAME}
    Example: HOMEASSISTANT_API_URL, HOMEASSISTANT_ENTITY_COUNT_WARN
    
    Args:
        app_name: Module app name (lowercase)
        
    Returns:
        Dict of configuration values
    """
    config = {}
    prefix = app_name.upper() + "_"
    
    # Scan environment variables for matching prefix
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # Extract the setting name (after the prefix)
            setting_name = key[len(prefix):].lower()
            
            # Try to convert to appropriate type
            # Bool: "true"/"false"
            if value.lower() in ("true", "false"):
                config[setting_name] = value.lower() == "true"
            # Int: numeric without decimal
            elif value.isdigit():
                config[setting_name] = int(value)
            # Float: numeric with decimal
            elif _is_float(value):
                config[setting_name] = float(value)
            # String: everything else
            else:
                config[setting_name] = value
    
    logger.debug(f"Loaded config for {app_name}: {len(config)} settings")
    return config


def _is_float(value: str) -> bool:
    """Check if a string can be converted to float."""
    try:
        float(value)
        return '.' in value  # Distinguish from int
    except ValueError:
        return False


# Module discovery cache (populated on first import)
_discovered_modules: List[Type[AppModule]] = []


def get_discovered_modules() -> List[Type[AppModule]]:
    """
    Get the list of discovered modules.
    
    Modules are discovered once on first call and cached.
    To force re-discovery, clear the cache first.
    
    Returns:
        List of discovered AppModule classes
    """
    global _discovered_modules
    
    if not _discovered_modules:
        _discovered_modules = discover_available_modules()
    
    return _discovered_modules


def clear_module_cache():
    """
    Clear the module discovery cache.
    
    Call this to force re-discovery of modules (useful for testing).
    """
    global _discovered_modules
    _discovered_modules = []
    logger.debug("Module cache cleared")
