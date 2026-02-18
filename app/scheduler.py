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
from datetime import date, datetime, time as _time
from typing import Dict, Any, Optional

from app.collectors import (
    collect_all_system_metrics,
    check_all_services,
    collect_all_docker_metrics,
    collect_all_smart_metrics,
    collect_all_raid_metrics,
    collect_all_app_metrics,
)
from app.alerts import process_alert

logger = logging.getLogger(__name__)

# Configuration - read from environment variables
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
SMART_POLL_INTERVAL = int(os.getenv("SMART_POLL_INTERVAL", "600"))
RAID_POLL_INTERVAL = int(os.getenv("RAID_POLL_INTERVAL", "120"))  # 2 minutes default

# Tracking variable for morning summary (prevents duplicates)
_last_summary_sent: datetime = None
_last_cleanup_date: Optional[date] = None  # Tracks last nightly cleanup date

# Validate intervals (minimum 10 seconds to prevent hammering)
if POLL_INTERVAL < 10:
    logger.warning(f"POLL_INTERVAL too low ({POLL_INTERVAL}s), using 10s minimum")
    POLL_INTERVAL = 10

if SMART_POLL_INTERVAL < 60:
    logger.warning(f"SMART_POLL_INTERVAL too low ({SMART_POLL_INTERVAL}s), using 60s minimum")
    SMART_POLL_INTERVAL = 60

if RAID_POLL_INTERVAL < 60:
    logger.warning(f"RAID_POLL_INTERVAL too low ({RAID_POLL_INTERVAL}s), using 60s minimum")
    RAID_POLL_INTERVAL = 60


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


async def collect_app_with_alerts() -> Dict[str, Any]:
    """
    Collect app module metrics and process alerts for any status changes.
    
    This function:
    1. Discovers available app modules (Home Assistant, qBittorrent, etc.)
    2. Matches modules to running Docker containers
    3. Collects app-specific metrics from each module
    4. Writes results to the database
    5. Processes alerts for each metric that has a status change
    
    Returns:
        Dict[str, Any]: Collection results with all app module metrics
    
    Raises:
        Exception: May raise exceptions which should be caught by caller
    """
    results = await collect_all_app_metrics()
    
    # Alerts are processed inside collect_all_app_metrics for each metric
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
    4. Collect app module metrics with alerting
    5. Collect SMART drive metrics (less frequently) with alerting
    
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
    
    # Collect app module metrics with alerts
    try:
        app_results = await collect_app_with_alerts()
        logger.debug(f"App module collection completed: {len(app_results)} modules")
    except Exception as e:
        logger.error(f"App module collection failed: {e}", exc_info=True)


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


async def collect_raid_cycle() -> None:
    """
    Run RAID collector (more frequently than SMART, less than system).
    
    RAID array status can change quickly (drive failure), so we collect
    more frequently than SMART but less than system metrics. This provides
    early warning of array degradation.
    """
    try:
        raid_results = await collect_all_raid_metrics()
        logger.debug(f"RAID collection completed: {len(raid_results)} arrays")
    except Exception as e:
        logger.error(f"RAID collection failed: {e}", exc_info=True)


async def check_morning_summary() -> None:
    """
    Check if it's time to send the morning summary digest.
    
    This function:
    1. Checks if current time matches configured SLEEP_SUMMARY_TIME
    2. Prevents duplicate sends within 5 minutes
    3. Generates summary from queued sleep events
    4. Sends summary to Discord
    5. Clears processed sleep events
    
    Runs every scheduler cycle (typically every 60 seconds) and sends
    summary when the configured wake time is reached.
    
    Duplicate Prevention:
    - Tracks last send time in module-level variable
    - Skips if summary already sent within last 5 minutes
    - Prevents duplicate sends when scheduler runs at 5:59 and 6:00
    """
    global _last_summary_sent
    
    from datetime import time
    from app.alerts.sleep_schedule import generate_morning_summary
    from app.alerts.discord import send_alert_async
    
    summary_time_str = os.getenv("SLEEP_SUMMARY_TIME", "")
    
    if not summary_time_str:
        return
    
    # Check if summary is enabled
    summary_enabled = os.getenv("SLEEP_SUMMARY_ENABLED", "true").lower() == "true"
    if not summary_enabled:
        return
    
    # Parse summary time
    try:
        parts = summary_time_str.strip().split(':')
        if len(parts) != 2:
            return
        hour, minute = int(parts[0]), int(parts[1])
        summary_time = time(hour, minute)
    except:
        logger.warning(f"Invalid SLEEP_SUMMARY_TIME: {summary_time_str}")
        return
    
    now = datetime.now()
    current_time = now.time()
    
    # Check if we're within 1 minute of summary time
    # This prevents duplicate sends if scheduler runs multiple times per minute
    time_diff = abs(
        (current_time.hour * 60 + current_time.minute) - 
        (summary_time.hour * 60 + summary_time.minute)
    )
    
    if time_diff <= 1:
        # Check if already sent recently (prevents duplicates)
        if _last_summary_sent:
            time_since_last = (now - _last_summary_sent).total_seconds()
            if time_since_last < 300:  # 5 minutes
                logger.debug(
                    f"Morning summary already sent {time_since_last:.0f}s ago, skipping duplicate"
                )
                return
        
        logger.info("Morning summary time reached, generating report...")
        
        try:
            # Generate and send summary
            embed = await generate_morning_summary()
            
            if embed:
                webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
                if webhook_url:
                    success = await send_alert_async(webhook_url, embed)
                    if success:
                        _last_summary_sent = now  # Update last sent time
                        logger.info("Morning summary sent successfully")
                    else:
                        logger.error("Failed to send morning summary")
                else:
                    logger.warning("Discord webhook not configured, skipping morning summary")
        except Exception as e:
            logger.error(f"Error generating/sending morning summary: {e}", exc_info=True)


async def run_nightly_cleanup() -> None:
    """
    Delete metrics_samples and service_status rows beyond the retention window.

    Reads METRICS_RETENTION_DAYS from the environment (default: 30).
    Setting it to 0 disables cleanup entirely (logs a WARNING).

    Intended to run once per day at 3:00 AM, called from the main scheduler
    loop.  Uses _last_cleanup_date to ensure it fires only once even if the
    scheduler wakes up multiple times within the same minute.
    """
    from app.storage.db import delete_old_metrics

    retention_days_str = os.getenv("METRICS_RETENTION_DAYS", "30").strip()
    try:
        retention_days = int(retention_days_str)
    except ValueError:
        logger.warning(
            "Invalid METRICS_RETENTION_DAYS value '%s' — using default 30",
            retention_days_str,
        )
        retention_days = 30

    if retention_days <= 0:
        logger.warning(
            "METRICS_RETENTION_DAYS is %d — nightly cleanup is DISABLED. "
            "metrics_samples will grow indefinitely.",
            retention_days,
        )
        return

    logger.info("Running nightly data retention cleanup (retention: %d days)...", retention_days)
    metrics_deleted, service_deleted = await delete_old_metrics(retention_days)
    logger.info(
        "Nightly cleanup complete: %d metrics_samples + %d service_status rows removed",
        metrics_deleted,
        service_deleted,
    )


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
    global _last_cleanup_date
    logger.info("=" * 60)
    logger.info("Scheduler started - autonomous monitoring active")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"SMART interval: {SMART_POLL_INTERVAL} seconds")
    logger.info(f"RAID interval: {RAID_POLL_INTERVAL} seconds")
    logger.info("=" * 60)
    
    # Calculate how many cycles to wait between SMART and RAID collections
    # Example: POLL_INTERVAL=60s, SMART_POLL_INTERVAL=600s -> collect every 10 cycles
    smart_cycle_interval = max(1, SMART_POLL_INTERVAL // POLL_INTERVAL)
    raid_cycle_interval = max(1, RAID_POLL_INTERVAL // POLL_INTERVAL)
    logger.info(f"SMART collection will run every {smart_cycle_interval} cycles")
    logger.info(f"RAID collection will run every {raid_cycle_interval} cycles")
    
    # Perform initial collection immediately (don't wait for first interval)
    logger.info("Performing initial collection...")
    try:
        start_time = datetime.now()
        await collect_and_alert()
        await collect_smart_cycle()  # Also collect SMART data on startup
        await collect_raid_cycle()   # Also collect RAID data on startup
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
            
            # Run RAID collection every Nth cycle
            if cycle_count % raid_cycle_interval == 0:
                logger.info(f"Running RAID collection (cycle #{cycle_count})")
                await collect_raid_cycle()
            
            # Check for morning summary (run every cycle)
            await check_morning_summary()

            # Run nightly data retention cleanup at 3:00 AM (once per day)
            today = datetime.now().date()
            if _last_cleanup_date != today and datetime.now().time() >= _time(3, 0):
                await run_nightly_cleanup()
                _last_cleanup_date = today

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
