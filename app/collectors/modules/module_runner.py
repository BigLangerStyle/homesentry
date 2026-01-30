"""
Module execution engine.

Handles discovering, loading, and running app modules with proper
error isolation and limit enforcement.
"""

import logging
import time
from typing import Dict, Any, List, Type
import docker

from app.collectors.modules import get_discovered_modules, load_module_config
from app.collectors.modules.base import AppModule
from app.storage.db import insert_metric_sample
from app.alerts.rules import process_alert

logger = logging.getLogger(__name__)


class APICallLimitExceeded(Exception):
    """Raised when a module exceeds the API call limit."""
    pass


async def collect_all_app_metrics() -> Dict[str, Any]:
    """
    Discover and run all app modules for matching containers.
    
    This is called by the scheduler alongside other collectors.
    
    Process:
    1. Discover available modules
    2. Get running Docker containers
    3. Match modules to containers
    4. Run each module's collect()
    5. Store metrics in database
    6. Process alerts
    
    Returns:
        Dict of {module_name: result} for all modules
    """
    results = {}
    
    try:
        # Discover available modules
        modules = get_discovered_modules()
        
        if not modules:
            logger.debug("No app modules discovered")
            return results
        
        # Get Docker client
        try:
            client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            return results
        
        # Get running containers
        try:
            containers = client.containers.list()
        except Exception as e:
            logger.error(f"Failed to list Docker containers: {e}")
            return results
        
        # Match modules to containers and run collections
        for module_class in modules:
            app_name = module_class.APP_NAME
            
            # Load module configuration
            config = load_module_config(app_name)
            
            # Find matching containers
            matched_containers = [
                c for c in containers 
                if module_class.detect(c)
            ]
            
            if not matched_containers:
                logger.debug(
                    f"No running containers found for module {app_name} "
                    f"(looking for: {', '.join(module_class.CONTAINER_NAMES)})"
                )
                continue
            
            # Run module for each matched container
            for container in matched_containers:
                try:
                    result = await run_module(module_class, container, config)
                    results[f"{app_name}_{container.name}"] = result
                    
                    # Store metrics in database if collection was successful
                    if result.get('status') == 'success':
                        await store_module_metrics(
                            app_name=app_name,
                            container_name=container.name,
                            metrics=result.get('metrics', {}),
                            config=config
                        )
                    
                except Exception as e:
                    logger.error(
                        f"Failed to run module {app_name} for container {container.name}: {e}",
                        exc_info=True
                    )
                    results[f"{app_name}_{container.name}"] = {
                        'status': 'error',
                        'error': str(e)
                    }
        
        return results
        
    except Exception as e:
        logger.error(f"App module collection failed: {e}", exc_info=True)
        return results


async def run_module(
    module_class: Type[AppModule],
    container,
    config: dict
) -> Dict[str, Any]:
    """
    Execute a single module with error isolation and limit enforcement.
    
    This wrapper ensures:
    - Module failures don't crash the system
    - Hard limits are enforced (10 metrics, 3 API calls)
    - Execution time is tracked
    - Errors are logged clearly
    
    Args:
        module_class: AppModule subclass (not instance)
        container: Docker container object
        config: Module configuration dict
        
    Returns:
        Dict with module results or error details
    """
    app_name = module_class.APP_NAME
    start_time = time.time()
    
    try:
        # Enforce config option limit
        if len(config) > module_class.MAX_CONFIG_OPTIONS:
            logger.warning(
                f"{app_name}: Too many config options "
                f"({len(config)} > {module_class.MAX_CONFIG_OPTIONS}), truncating"
            )
            config = dict(list(config.items())[:module_class.MAX_CONFIG_OPTIONS])
        
        # Validate configuration
        module_instance = module_class()
        is_valid, error_msg = module_instance.validate_config(config)
        if not is_valid:
            logger.error(f"{app_name}: Configuration validation failed: {error_msg}")
            return {
                'status': 'error',
                'error': f"Configuration validation failed: {error_msg}"
            }
        
        # Run module collection
        metrics = await module_instance.collect(container, config)
        
        # Enforce metric limit
        if len(metrics) > module_class.MAX_METRICS:
            logger.warning(
                f"{app_name}: Too many metrics "
                f"({len(metrics)} > {module_class.MAX_METRICS}), truncating"
            )
            metrics = dict(list(metrics.items())[:module_class.MAX_METRICS])
        
        execution_time = time.time() - start_time
        
        return {
            'status': 'success',
            'metrics': metrics,
            'execution_time_ms': round(execution_time * 1000, 2),
            'container_name': container.name
        }
        
    except APICallLimitExceeded as e:
        logger.error(f"{app_name}: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    
    except Exception as e:
        logger.error(
            f"Module {app_name} failed for container {container.name}: {e}",
            exc_info=True
        )
        return {
            'status': 'error',
            'error': str(e)
        }


async def store_module_metrics(
    app_name: str,
    container_name: str,
    metrics: Dict[str, Any],
    config: dict
) -> None:
    """
    Store module metrics in the database and process alerts.
    
    Args:
        app_name: Module app name (e.g., 'homeassistant')
        container_name: Container name
        metrics: Dict of {metric_name: value}
        config: Module configuration for threshold checking
    """
    for metric_name, value in metrics.items():
        # Construct full metric name: app_containerName_metricName
        # Example: homeassistant_homeassistant_entity_count
        full_metric_name = f"{app_name}_{metric_name}"
        
        # Determine if value is numeric or text
        value_num = None
        value_text = None
        if isinstance(value, (int, float)):
            value_num = float(value)
        else:
            value_text = str(value)
        
        # Determine status based on thresholds (if configured)
        status = determine_metric_status(
            app_name=app_name,
            metric_name=metric_name,
            value=value,
            config=config
        )
        
        try:
            # Store in database
            await insert_metric_sample(
                category='app',
                name=full_metric_name,
                value_num=value_num,
                value_text=value_text,
                status=status,
                details_json=None
            )
            
            # Process alert
            await process_alert(
                category='app',
                name=full_metric_name,
                new_status=status,
                details={
                    'app_name': app_name,
                    'container_name': container_name,
                    'metric_name': metric_name,
                    'value': value
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to store metric {full_metric_name}: {e}",
                exc_info=True
            )


def determine_metric_status(
    app_name: str,
    metric_name: str,
    value: Any,
    config: dict
) -> str:
    """
    Determine metric status (OK/WARN/FAIL) based on configured thresholds.
    
    Looks for environment variables like:
    - HOMEASSISTANT_ENTITY_COUNT_WARN=500
    - HOMEASSISTANT_ENTITY_COUNT_FAIL=1000
    
    Args:
        app_name: Module app name
        metric_name: Metric name
        value: Metric value
        config: Module configuration dict
        
    Returns:
        Status string: 'OK', 'WARN', or 'FAIL'
    """
    # Only apply thresholds to numeric values
    if not isinstance(value, (int, float)):
        return 'OK'
    
    # Look for threshold config
    warn_key = f"{metric_name}_warn"
    fail_key = f"{metric_name}_fail"
    
    warn_threshold = config.get(warn_key)
    fail_threshold = config.get(fail_key)
    
    # Check FAIL threshold first (more severe)
    if fail_threshold is not None:
        try:
            if isinstance(fail_threshold, (int, float)) and value >= fail_threshold:
                return 'FAIL'
        except (ValueError, TypeError):
            pass
    
    # Check WARN threshold
    if warn_threshold is not None:
        try:
            if isinstance(warn_threshold, (int, float)) and value >= warn_threshold:
                return 'WARN'
        except (ValueError, TypeError):
            pass
    
    return 'OK'
