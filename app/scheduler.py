"""
Background scheduler for HomeSentry

Runs collectors at configured intervals and processes alerts automatically.
This makes HomeSentry an autonomous monitoring system that operates 24/7.

The scheduler:
- Runs system and service collectors on a configurable interval
- Processes alerts automatically after each collection
- Handles collector failures gracefully (continues running)
- Supports graceful startup and shutdown
- Sleeps intelligently (accounts for collection duration)
"""
import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Any

from app.collectors import (
    collect_all_system_metrics,
    check_all_services,
    collect_all_docker_metrics,
    collect_all_smart_metrics
)
from app.alerts import process_alert

logger = logging.getLogger(__name__)

# Configuration - read from environment variables
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
SMART_POLL_INTERVAL = int(os.getenv("SMART_POLL_INTERVAL", "600"))  # Future use

# Validate intervals (minimum 10 seconds to prevent hammering)
if POLL_INTERVAL < 10:
    logger.warning(f"POLL_INTERVAL too low ({POLL_INTERVAL}s), using 10s minimum")
    POLL_INTERVAL = 10

if SMART_POLL_INTERVAL < 60:
    logger.warning(f"SMART_POLL_INTERVAL too low ({SMART_POLL_INTERVAL}s), using 60s minimum")
    SMART_POLL_INTERVAL = 60


async def collect_system_with_alerts() -> Dict[str, Any]:
    """
    Collect system metrics and process alerts for any status changes.
    
    This function:
    1. Collects CPU, memory, and disk metrics
    2. Writes them to the database
    3. Processes alerts for each metric that has a status change
    
    Returns:
        Dict[str, Any]: Collection results with all metrics
    
    Raises:
        Exception: May raise exceptions which should be caught by caller
    """
    results = await collect_all_system_metrics()
    
    # Process alerts for each metric that has status information
    for metric_name, data in results.items():
        if data and isinstance(data, dict) and 'status' in data:
            try:
                await process_alert(
                    category='system',
                    name=metric_name,
                    new_status=data['status'],
                    details=data
                )
            except Exception as e:
                logger.error(f"Failed to process alert for {metric_name}: {e}")
    
    return results


async def collect_services_with_alerts() -> Dict[str, Any]:
    """
    Collect service health checks and process alerts for any status changes.
    
    This function:
    1. Checks all configured services (Plex, Jellyfin, Pi-hole, etc.)
    2. Writes results to the database
    3. Processes alerts for each service that has a status change
    
    Returns:
        Dict[str, Any]: Collection results with all service check results
    
    Raises:
        Exception: May raise exceptions which should be caught by caller
    """
    results = await check_all_services()
    
    # Process alerts for each service that has status information
    for service_name, data in results.items():
        if data and isinstance(data, dict) and 'status' in data:
            try:
                await process_alert(
                    category='service',
                    name=service_name,
                    new_status=data['status'],
                    details=data
                )
            except Exception as e:
                logger.error(f"Failed to process alert for service {service_name}: {e}")
    
    return results


async def collect_docker_with_alerts() -> Dict[str, Any]:
    """
    Collect Docker container metrics and process alerts for any status changes.
    
    This function:
    1. Collects container status, health, restarts, and resource usage
    2. Writes results to the database
    3. Processes alerts for each container that has a status change
    
    Returns:
        Dict[str, Any]: Collection results with all container metrics
    
    Raises:
        Exception: May raise exceptions which should be caught by caller
    """
    results = await collect_all_docker_metrics()
    
    # Alerts are processed inside collect_all_docker_metrics for each container
    # No additional alert processing needed here
    
    return results


async def collect_smart_with_alerts() -> Dict[str, Any]:
    """
    Collect SMART drive health metrics and process alerts for any status changes.
    
    This function:
    1. Collects SMART health, temperature, and critical attributes for all drives
    2. Writes results to the database
    3. Processes alerts for drives with status changes
    
    Returns:
        Dict[str, Any]: Collection results with all drive SMART data
    
    Raises:
        Exception: May raise exceptions which should be caught by caller
    """
    results = await collect_all_smart_metrics()
    
    # Alerts are processed inside collect_all_smart_metrics for each drive
    # No additional alert processing needed here
    
    return results


async def collect_and_alert() -> None:
    """
    Run all collectors and process alerts.
    
    This orchestrates the full collection cycle:
    1. Collect system metrics (CPU, RAM, disk) with alerting
    2. Collect service health checks with alerting
    3. Collect Docker container metrics with alerting
    4. Collect SMART drive metrics (less frequently) with alerting
    
    Each collector runs independently - if one fails, the others still run.
    Errors are logged but don't stop the collection cycle.
    """
    # Collect system metrics with alerts
    try:
        system_results = await collect_system_with_alerts()
        logger.debug(f"System collection completed: {len(system_results)} metrics")
    except Exception as e:
        logger.error(f"System collection failed: {e}", exc_info=True)
    
    # Collect service health with alerts
    try:
        service_results = await collect_services_with_alerts()
        logger.debug(f"Service collection completed: {len(service_results)} services")
    except Exception as e:
        logger.error(f"Service collection failed: {e}", exc_info=True)
    
    # Collect Docker container metrics with alerts
    try:
        docker_results = await collect_docker_with_alerts()
        logger.debug(f"Docker collection completed: {len(docker_results)} containers")
    except Exception as e:
        logger.error(f"Docker collection failed: {e}", exc_info=True)


async def collect_smart_cycle() -> None:
    """
    Run SMART collector (less frequently than other collectors).
    
    SMART data doesn't change rapidly, so we collect it less frequently
    to avoid unnecessary disk activity. This function is called separately
    from the main collection cycle.
    """
    try:
        smart_results = await collect_smart_with_alerts()
        logger.debug(f"SMART collection completed: {len(smart_results)} drives")
    except Exception as e:
        logger.error(f"SMART collection failed: {e}", exc_info=True)


async def run_scheduler() -> None:
    """
    Main scheduler loop - runs forever until cancelled.
    
    This is the heart of HomeSentry's autonomous monitoring:
    - Runs collectors at POLL_INTERVAL (default: 60 seconds)
    - Performs initial collection immediately on startup
    - Accounts for collection time when sleeping
    - Handles cancellation gracefully
    - Continues running even if collectors fail
    
    The scheduler runs in the background as an asyncio task and is cancelled
    during application shutdown.
    """
    logger.info("=" * 60)
    logger.info("Scheduler started - autonomous monitoring active")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"SMART interval: {SMART_POLL_INTERVAL} seconds")
    logger.info("=" * 60)
    
    # Calculate how many cycles to wait between SMART collections
    # Example: POLL_INTERVAL=60s, SMART_POLL_INTERVAL=600s -> collect every 10 cycles
    smart_cycle_interval = max(1, SMART_POLL_INTERVAL // POLL_INTERVAL)
    logger.info(f"SMART collection will run every {smart_cycle_interval} cycles")
    
    # Perform initial collection immediately (don't wait for first interval)
    logger.info("Performing initial collection...")
    try:
        start_time = datetime.now()
        await collect_and_alert()
        await collect_smart_cycle()  # Also collect SMART data on startup
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Initial collection completed in {elapsed:.2f}s")
    except Exception as e:
        logger.error(f"Initial collection failed: {e}", exc_info=True)
    
    # Main scheduler loop
    cycle_count = 0
    while True:
        try:
            # Wait for next interval
            logger.debug(f"Sleeping {POLL_INTERVAL}s until next collection...")
            await asyncio.sleep(POLL_INTERVAL)
            
            # Start collection cycle
            cycle_count += 1
            logger.info(f"Collection cycle #{cycle_count} started")
            start_time = datetime.now()
            
            # Run regular collectors and process alerts
            await collect_and_alert()
            
            # Run SMART collection every Nth cycle
            if cycle_count % smart_cycle_interval == 0:
                logger.info(f"Running SMART collection (cycle #{cycle_count})")
                await collect_smart_cycle()
            
            # Calculate elapsed time
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Collection cycle #{cycle_count} completed in {elapsed:.2f}s")
            
            # Warn if collection took longer than poll interval
            if elapsed > POLL_INTERVAL * 0.8:
                logger.warning(
                    f"Collection took {elapsed:.2f}s, which is {(elapsed/POLL_INTERVAL)*100:.1f}% "
                    f"of poll interval ({POLL_INTERVAL}s). Consider increasing POLL_INTERVAL."
                )
            
        except asyncio.CancelledError:
            logger.info("Scheduler cancelled - stopping gracefully")
            logger.info(f"Total cycles completed: {cycle_count}")
            break
        except Exception as e:
            logger.error(f"Scheduler error in cycle #{cycle_count}: {e}", exc_info=True)
            logger.info(f"Continuing after error - will retry in {POLL_INTERVAL}s")
            # Continue running even after errors - this is critical for reliability
