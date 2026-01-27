"""
Docker Container Monitoring Collector for HomeSentry

Monitors Docker containers on the host system including:
- Container status (running, stopped, paused, restarting, dead)
- Health check status (healthy, unhealthy, starting, none)
- Restart counts (to detect crash-looping containers)
- CPU and memory usage per container
"""
import logging
import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from app.storage import insert_metric_sample
from app.alerts import process_alert

logger = logging.getLogger(__name__)

# Configuration from environment variables
DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")
DOCKER_COLLECTION_ENABLED = os.getenv("DOCKER_COLLECTION_ENABLED", "true").lower() == "true"

# Resource thresholds (for future use - v0.2.0 focuses on status/health)
DOCKER_CPU_WARN_THRESHOLD = float(os.getenv("DOCKER_CPU_WARN_THRESHOLD", "80"))
DOCKER_CPU_FAIL_THRESHOLD = float(os.getenv("DOCKER_CPU_FAIL_THRESHOLD", "95"))
DOCKER_MEMORY_WARN_THRESHOLD = float(os.getenv("DOCKER_MEMORY_WARN_THRESHOLD", "80"))
DOCKER_MEMORY_FAIL_THRESHOLD = float(os.getenv("DOCKER_MEMORY_FAIL_THRESHOLD", "95"))


# ============================================================================
# Helper Functions
# ============================================================================

def get_docker_client() -> Optional[docker.DockerClient]:
    """
    Get Docker client connection.
    
    Returns:
        docker.DockerClient: Connected Docker client, or None if connection fails
    """
    if not DOCKER_AVAILABLE:
        logger.error("Docker library not installed - cannot monitor containers")
        return None
    
    if not DOCKER_COLLECTION_ENABLED:
        logger.debug("Docker collection is disabled in configuration")
        return None
    
    try:
        # Connect to Docker daemon via Unix socket
        client = docker.DockerClient(base_url=f"unix://{DOCKER_SOCKET_PATH}")
        
        # Verify connection by pinging Docker
        client.ping()
        
        return client
    
    except DockerException as e:
        logger.error(f"Failed to connect to Docker daemon at {DOCKER_SOCKET_PATH}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to Docker: {e}")
        return None


def extract_container_health_status(container) -> str:
    """
    Extract health check status from container.
    
    Args:
        container: Docker container object
    
    Returns:
        str: Health status - "healthy", "unhealthy", "starting", or "none"
    """
    try:
        # Container health status is in attrs -> State -> Health -> Status
        health = container.attrs.get("State", {}).get("Health", {})
        
        if not health:
            return "none"  # No health check configured
        
        status = health.get("Status", "none").lower()
        
        # Normalize status strings
        if status in ["healthy", "unhealthy", "starting"]:
            return status
        
        return "none"
    
    except Exception as e:
        logger.debug(f"Could not extract health status for {container.name}: {e}")
        return "none"


def calculate_cpu_percent(stats: Dict) -> Optional[float]:
    """
    Calculate CPU usage percentage from Docker stats.
    
    Docker provides cumulative CPU usage, so we need to calculate the percentage
    based on the delta between measurements and available CPU cores.
    
    Args:
        stats: Docker container stats dict
    
    Returns:
        float: CPU usage percentage (0-100 * num_cores), or None if calculation fails
    """
    try:
        # Extract CPU stats
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        
        cpu_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        precpu_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        
        system_usage = cpu_stats.get("system_cpu_usage", 0)
        presystem_usage = precpu_stats.get("system_cpu_usage", 0)
        
        # Calculate deltas
        cpu_delta = cpu_usage - precpu_usage
        system_delta = system_usage - presystem_usage
        
        # Prevent division by zero
        if system_delta <= 0 or cpu_delta < 0:
            return 0.0
        
        # Number of CPU cores
        num_cpus = cpu_stats.get("online_cpus", len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1])))
        
        if num_cpus == 0:
            num_cpus = 1
        
        # Calculate percentage
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
        
        return round(cpu_percent, 2)
    
    except Exception as e:
        logger.debug(f"Could not calculate CPU percentage: {e}")
        return None


def extract_memory_usage(stats: Dict) -> tuple[Optional[float], Optional[float]]:
    """
    Extract memory usage from Docker stats.
    
    Args:
        stats: Docker container stats dict
    
    Returns:
        tuple: (memory_mb, memory_limit_mb) or (None, None) if extraction fails
    """
    try:
        memory_stats = stats.get("memory_stats", {})
        
        # Current memory usage (in bytes)
        usage = memory_stats.get("usage", 0)
        
        # Memory limit (in bytes)
        limit = memory_stats.get("limit", 0)
        
        # Convert to MB
        memory_mb = round(usage / (1024 ** 2), 2)
        memory_limit_mb = round(limit / (1024 ** 2), 2) if limit > 0 else None
        
        return memory_mb, memory_limit_mb
    
    except Exception as e:
        logger.debug(f"Could not extract memory usage: {e}")
        return None, None


def determine_container_status(
    state: str,
    health_status: str,
    restart_count: int,
    previous_restart_count: Optional[int] = None
) -> str:
    """
    Determine overall container status based on state, health, and restart count.
    
    Args:
        state: Container state (running, stopped, paused, restarting, dead)
        health_status: Health check status (healthy, unhealthy, starting, none)
        restart_count: Current restart count
        previous_restart_count: Previous restart count (for detecting rapid restarts)
    
    Returns:
        str: Status - "OK", "WARN", or "FAIL"
    
    Status determination logic:
        - FAIL: Container stopped, dead, or unhealthy
        - WARN: Container starting, paused, or recently restarted
        - OK: Container running and healthy (or no health check)
    """
    # FAIL conditions
    if state in ["stopped", "dead"]:
        return "FAIL"
    
    if health_status == "unhealthy":
        return "FAIL"
    
    # WARN conditions
    if state == "paused":
        return "WARN"
    
    if state == "restarting":
        return "WARN"
    
    if health_status == "starting":
        return "WARN"
    
    # Check for rapid restarts (crash-looping)
    if previous_restart_count is not None and restart_count > previous_restart_count:
        # Container restarted since last check
        return "WARN"
    
    # OK: running and healthy (or no health check)
    if state == "running" and health_status in ["healthy", "none"]:
        return "OK"
    
    # Default to WARN for unexpected states
    return "WARN"


# ============================================================================
# Synchronous Collection Functions (run in thread pool)
# ============================================================================

def _sync_collect_container_info(container) -> Optional[Dict[str, Any]]:
    """
    Collect detailed information about a single container (synchronous).
    
    This runs in a thread pool to avoid blocking the async event loop.
    
    Args:
        container: Docker container object
    
    Returns:
        Dict with container information, or None on failure
    """
    try:
        # Reload container to get fresh state
        container.reload()
        
        # Extract basic information
        container_id = container.id
        container_name = container.name
        state = container.status  # running, stopped, paused, restarting, dead
        
        # Extract health check status
        health_status = extract_container_health_status(container)
        
        # Extract restart count
        restart_count = container.attrs.get("RestartCount", 0)
        
        # Get resource usage stats (non-streaming, single snapshot)
        stats = None
        cpu_percent = None
        memory_mb = None
        memory_limit_mb = None
        
        if state == "running":
            try:
                stats = container.stats(stream=False, decode=True)
                cpu_percent = calculate_cpu_percent(stats)
                memory_mb, memory_limit_mb = extract_memory_usage(stats)
            except Exception as e:
                logger.debug(f"Could not get stats for {container_name}: {e}")
        
        return {
            "container_id": container_id,
            "container_name": container_name,
            "state": state,
            "health_status": health_status,
            "restart_count": restart_count,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "memory_limit_mb": memory_limit_mb,
        }
    
    except NotFound:
        logger.warning(f"Container disappeared during collection: {container.name}")
        return None
    except Exception as e:
        logger.error(f"Failed to collect info for container {container.name}: {e}")
        return None


def _sync_list_containers(client: docker.DockerClient) -> List:
    """
    List all containers (synchronous).
    
    Args:
        client: Docker client
    
    Returns:
        List of container objects
    """
    try:
        # Get all containers (including stopped ones)
        return client.containers.list(all=True)
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        return []


# ============================================================================
# Async Collection Functions
# ============================================================================

async def collect_container_metrics(client: docker.DockerClient) -> Dict[str, Dict[str, Any]]:
    """
    Collect metrics for all Docker containers.
    
    Args:
        client: Docker client
    
    Returns:
        Dict keyed by container name with container metrics
    """
    results = {}
    
    # Get list of containers in thread pool
    loop = asyncio.get_event_loop()
    containers = await loop.run_in_executor(None, _sync_list_containers, client)
    
    if not containers:
        logger.info("No Docker containers found")
        return results
    
    logger.info(f"Collecting metrics for {len(containers)} containers...")
    
    # Collect info for each container concurrently
    tasks = [
        loop.run_in_executor(None, _sync_collect_container_info, container)
        for container in containers
    ]
    
    container_infos = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for container_info in container_infos:
        if isinstance(container_info, Exception):
            logger.error(f"Container collection failed: {container_info}")
            continue
        
        if container_info is None:
            continue
        
        container_name = container_info["container_name"]
        results[container_name] = container_info
        
        # Determine status
        status = determine_container_status(
            container_info["state"],
            container_info["health_status"],
            container_info["restart_count"]
        )
        
        # Log collection result
        logger.info(
            f"Container [{container_name}]: {status} "
            f"(state: {container_info['state']}, "
            f"health: {container_info['health_status']}, "
            f"restarts: {container_info['restart_count']})"
        )
        
        # Store status metric in database
        await store_container_status_metric(container_info, status)
        
        # Store resource metrics if available
        if container_info["cpu_percent"] is not None:
            await store_container_cpu_metric(container_info)
        
        if container_info["memory_mb"] is not None:
            await store_container_memory_metric(container_info)
        
        # Process alerts for status changes
        await process_container_alert(container_info, status)
    
    return results


async def store_container_status_metric(container_info: Dict[str, Any], status: str) -> None:
    """
    Store container status metric in database.
    
    Args:
        container_info: Container information dict
        status: Determined status (OK/WARN/FAIL)
    """
    try:
        details = {
            "container_id": container_info["container_id"],
            "container_name": container_info["container_name"],
            "state": container_info["state"],
            "health_status": container_info["health_status"],
            "restart_count": container_info["restart_count"],
        }
        
        # Status as numeric: 1 = running, 0 = not running
        value = 1 if container_info["state"] == "running" else 0
        
        await insert_metric_sample(
            category="docker",
            name=f"container_{container_info['container_name']}_status",
            value_num=value,
            status=status,
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store container status metric: {e}")


async def store_container_cpu_metric(container_info: Dict[str, Any]) -> None:
    """
    Store container CPU usage metric in database.
    
    Args:
        container_info: Container information dict
    """
    try:
        details = {
            "container_id": container_info["container_id"],
            "container_name": container_info["container_name"],
        }
        
        await insert_metric_sample(
            category="docker",
            name=f"container_{container_info['container_name']}_cpu",
            value_num=container_info["cpu_percent"],
            status="OK",  # Resource metrics don't have status (yet)
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store container CPU metric: {e}")


async def store_container_memory_metric(container_info: Dict[str, Any]) -> None:
    """
    Store container memory usage metric in database.
    
    Args:
        container_info: Container information dict
    """
    try:
        details = {
            "container_id": container_info["container_id"],
            "container_name": container_info["container_name"],
            "memory_limit_mb": container_info.get("memory_limit_mb"),
        }
        
        await insert_metric_sample(
            category="docker",
            name=f"container_{container_info['container_name']}_memory",
            value_num=container_info["memory_mb"],
            status="OK",  # Resource metrics don't have status (yet)
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store container memory metric: {e}")


async def process_container_alert(container_info: Dict[str, Any], status: str) -> None:
    """
    Process alerts for container status changes.
    
    Args:
        container_info: Container information dict
        status: Determined status (OK/WARN/FAIL)
    """
    try:
        alert_details = {
            "container_id": container_info["container_id"],
            "state": container_info["state"],
            "health_status": container_info["health_status"],
            "restart_count": container_info["restart_count"],
        }
        
        await process_alert(
            category="docker",
            name=container_info["container_name"],
            new_status=status,
            details=alert_details
        )
    
    except Exception as e:
        logger.error(f"Failed to process alert for container {container_info['container_name']}: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

async def collect_all_docker_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Collect all Docker container metrics.
    
    This is the main entry point for Docker monitoring. It connects to the
    Docker daemon, collects metrics for all containers, and stores them in
    the database.
    
    Returns:
        Dict with container metrics keyed by container name
        Example: {
            "jellyfin": {"state": "running", "health_status": "healthy", ...},
            "qbittorrent": {"state": "running", "health_status": "none", ...}
        }
    """
    timestamp = datetime.utcnow().isoformat()
    
    # Get Docker client
    client = get_docker_client()
    
    if client is None:
        logger.warning("Docker client unavailable - skipping Docker metrics collection")
        return {}
    
    try:
        # Collect metrics for all containers
        results = await collect_container_metrics(client)
        
        logger.info(f"Docker metrics collection complete: {len(results)} containers monitored")
        
        return results
    
    except Exception as e:
        logger.error(f"Docker metrics collection failed: {e}", exc_info=True)
        return {}
    
    finally:
        # Close Docker client
        try:
            client.close()
        except:
            pass
