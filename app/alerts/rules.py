"""
Alert rules engine for HomeSentry

This module handles intelligent state-change detection and alert triggering.
It prevents notification spam by only alerting when status changes, respecting
cooldown periods, and ensuring recovery notifications are always sent.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.storage import insert_event, get_latest_event_by_key, update_event_notified
from app.alerts.discord import (
    send_alert_async,
    format_service_alert,
    format_system_alert,
    format_disk_alert
)
from app.alerts.maintenance import should_suppress_alert

logger = logging.getLogger(__name__)

# Configuration from environment variables
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30"))
ALERTS_ENABLED = os.getenv("ALERTS_ENABLED", "true").lower() == "true"


def generate_event_key(category: str, name: str) -> str:
    """
    Generate unique event key from category and name.
    
    Event keys uniquely identify specific monitoring targets and are used
    to track state changes over time.
    
    Args:
        category: Event category (service, system, disk, smart, raid)
        name: Item name (plex, cpu, /mnt/Array, /dev/sda, etc.)
    
    Returns:
        str: Unique event key
    
    Examples:
        >>> generate_event_key("service", "plex")
        'service_plex'
        >>> generate_event_key("disk", "/mnt/Array")
        'disk_/mnt/array'
        >>> generate_event_key("system", "CPU")
        'system_cpu'
    """
    # Sanitize name: lowercase and replace spaces with underscores
    clean_name = name.replace(" ", "_").lower()
    return f"{category}_{clean_name}"


async def should_alert(
    event_key: str,
    prev_status: Optional[str],
    new_status: str,
    last_notified_ts: Optional[str],
    cooldown_minutes: int = ALERT_COOLDOWN_MINUTES
) -> bool:
    """
    Determine if alert should be sent based on state change and cooldown.
    
    Alert Logic:
    1. First detection (prev_status is None) - Always alert
    2. No status change (prev_status == new_status) - Don't alert
    3. Recovery (any status → OK) - Always alert
    4. Status worsened (OK→WARN, OK→FAIL, WARN→FAIL) - Always alert
    5. Status improved but not to OK (FAIL→WARN) - Check cooldown
    
    Args:
        event_key: Unique event identifier
        prev_status: Previous status (OK/WARN/FAIL) or None for first detection
        new_status: New status (OK/WARN/FAIL)
        last_notified_ts: ISO timestamp of last notification or None
        cooldown_minutes: Cooldown period in minutes (default from env)
    
    Returns:
        bool: True if alert should be sent, False otherwise
    
    Examples:
        >>> await should_alert("service_plex", None, "FAIL", None)
        True  # First detection
        >>> await should_alert("service_plex", "OK", "OK", None)
        False  # No change
        >>> await should_alert("service_plex", "FAIL", "OK", None)
        True  # Recovery
        >>> await should_alert("service_plex", "OK", "FAIL", None)
        True  # Worsened
    """
    # First time seeing this event - always alert
    if prev_status is None:
        logger.info(f"First detection for {event_key} ({new_status}) - will alert")
        return True
    
    # No status change - don't alert
    if prev_status == new_status:
        logger.debug(f"No status change for {event_key} ({new_status}) - no alert")
        return False
    
    # Recovery (any status → OK) - always alert
    if new_status == "OK":
        logger.info(f"Recovery detected for {event_key} ({prev_status} → OK) - will alert")
        return True
    
    # Status got worse - always alert
    status_order = {"OK": 0, "WARN": 1, "FAIL": 2}
    if status_order.get(new_status, 0) > status_order.get(prev_status, 0):
        logger.info(f"Status worsened for {event_key} ({prev_status} → {new_status}) - will alert")
        return True
    
    # Status improved but not to OK (e.g., FAIL → WARN) - check cooldown
    if last_notified_ts:
        try:
            last_notified = datetime.fromisoformat(last_notified_ts)
            time_since_alert = datetime.now() - last_notified
            
            if time_since_alert.total_seconds() < (cooldown_minutes * 60):
                logger.info(
                    f"Alert suppressed for {event_key} "
                    f"(in cooldown, {time_since_alert.total_seconds()/60:.1f} min since last alert)"
                )
                return False
        except Exception as e:
            logger.error(f"Error parsing timestamp {last_notified_ts}: {e}")
    
    # Outside cooldown or no previous notification - send alert
    logger.info(f"Status changed for {event_key} ({prev_status} → {new_status}) - will alert")
    return True


async def check_state_change(
    event_key: str,
    new_status: str,
    details: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Check if status changed and return event details.
    
    This function queries the database for the previous state and determines
    if there has been a state change.
    
    Args:
        event_key: Unique event identifier
        new_status: New status (OK/WARN/FAIL)
        details: Additional context for the event
    
    Returns:
        Dict with event details if state changed, None otherwise
        
    Example:
        >>> result = await check_state_change("service_plex", "FAIL", {"error": "timeout"})
        >>> if result:
        ...     print(f"Status changed from {result['prev_status']} to {result['new_status']}")
    """
    # Get last event for this key
    last_event = await get_latest_event_by_key(event_key)
    
    prev_status = last_event["new_status"] if last_event else None
    
    # Check if status changed
    if prev_status == new_status:
        logger.debug(f"No state change for {event_key}: {new_status}")
        return None
    
    return {
        "event_key": event_key,
        "prev_status": prev_status,
        "new_status": new_status,
        "last_notified_ts": last_event.get("notified_ts") if last_event else None,
        "details": details
    }


async def process_alert(
    category: str,
    name: str,
    new_status: str,
    details: Dict[str, Any]
) -> bool:
    """
    Process potential alert - check state change and send if needed.
    
    This is the main entry point for alert processing. It:
    1. Generates event key
    2. Checks previous state
    3. Determines if alert should be sent
    4. Formats and sends alert
    5. Updates event tracking in database
    
    Args:
        category: Alert category (service, system, disk, smart, raid)
        name: Item name (plex, cpu, /mnt/Array, /dev/sda, md0)
        new_status: New status (OK/WARN/FAIL)
        details: Additional details for alert message (varies by category)
            - For services: url, http_code, response_ms, error
            - For system: value, threshold, unit, message
            - For disk: free_gb, total_gb, percent_used, threshold_gb, threshold_pct
    
    Returns:
        bool: True if alert was sent, False otherwise
    
    Examples:
        >>> # Service alert
        >>> await process_alert("service", "plex", "FAIL", {
        ...     "url": "http://192.168.1.8:32400",
        ...     "error": "Connection timeout"
        ... })
        
        >>> # System alert
        >>> await process_alert("system", "cpu", "WARN", {
        ...     "value": 87,
        ...     "threshold": 80,
        ...     "unit": "%",
        ...     "message": "CPU usage is elevated"
        ... })
        
        >>> # Disk alert
        >>> await process_alert("disk", "/mnt/Array", "WARN", {
        ...     "free_gb": 48.5,
        ...     "total_gb": 7300,
        ...     "percent_used": 93.3,
        ...     "threshold_gb": 50,
        ...     "threshold_pct": 15
        ... })
    """
    # Check if alerts are enabled
    if not ALERTS_ENABLED:
        logger.debug("Alerts disabled via ALERTS_ENABLED configuration")
        return False
    
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured - alerts disabled")
        return False
    
    # Generate event key
    event_key = generate_event_key(category, name)
    
    # Get last event for this key
    last_event = await get_latest_event_by_key(event_key)
    
    prev_status = last_event["new_status"] if last_event else None
    last_notified_ts = last_event.get("notified_ts") if last_event else None
    
    # Check if we should alert
    if not await should_alert(event_key, prev_status, new_status, last_notified_ts):
        return False
    
    # Check if alert should be suppressed due to maintenance window
    suppress, reason = should_suppress_alert(category, name, new_status)
    
    if suppress:
        logger.info(f"Alert suppressed for {event_key}: {reason}")
        
        # Still log to database but mark as maintenance-suppressed
        message = f"{name}: {prev_status or 'Unknown'} → {new_status}"
        await insert_event(
            event_key=event_key,
            prev_status=prev_status,
            new_status=new_status,
            message=message,
            maintenance_suppressed=True
        )
        return False  # Don't send to Discord
    
    # Format alert message based on category
    if category == "service":
        embed = format_service_alert(name, prev_status, new_status, details)
    elif category == "disk":
        embed = format_disk_alert(name, prev_status, new_status, details)
    else:  # system, smart, raid, or other
        embed = format_system_alert(name, prev_status, new_status, details)
    
    # Send alert
    try:
        success = await send_alert_async(DISCORD_WEBHOOK_URL, embed)
        
        if success:
            # Insert event record (not maintenance-suppressed)
            message = embed.get("title", "Alert")
            await insert_event(
                event_key=event_key,
                prev_status=prev_status,
                new_status=new_status,
                message=message,
                maintenance_suppressed=False
            )
            
            # Mark as notified
            await update_event_notified(event_key)
            
            logger.info(f"Alert sent for {event_key}: {prev_status} → {new_status}")
        else:
            logger.error(f"Failed to send alert for {event_key}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error processing alert for {event_key}: {e}", exc_info=True)
        return False
