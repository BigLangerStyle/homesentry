"""
Sleep Schedule Management for HomeSentry

Provides complete alert suppression during sleep hours with optional
morning summary digest. Different from maintenance windows - this is
for long quiet periods (6-8 hours) rather than short maintenance events.

Configuration via environment variables:
    - SLEEP_SCHEDULE_ENABLED=true
    - SLEEP_SCHEDULE_START=00:00
    - SLEEP_SCHEDULE_END=07:30
    - SLEEP_SUMMARY_ENABLED=true
    - SLEEP_SUMMARY_TIME=07:30
    - SLEEP_ALLOW_CRITICAL_ALERTS=false
"""
import logging
import os
from datetime import datetime, time
from typing import Optional, Tuple, Dict, Any, List

logger = logging.getLogger(__name__)


def parse_sleep_time(time_str: str) -> Optional[time]:
    """
    Parse HH:MM time string.
    
    Args:
        time_str: String like "00:00" or "07:30"
        
    Returns:
        time object or None if invalid
        
    Examples:
        >>> parse_sleep_time("00:00")
        datetime.time(0, 0)
        >>> parse_sleep_time("07:30")
        datetime.time(7, 30)
        >>> parse_sleep_time("invalid")
        None
    """
    if not time_str or not isinstance(time_str, str):
        return None
    
    try:
        parts = time_str.strip().split(':')
        if len(parts) != 2:
            logger.warning(f"Invalid sleep time format (expected HH:MM): {time_str}")
            return None
        
        hour, minute = int(parts[0]), int(parts[1])
        
        # Validate ranges
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            logger.warning(f"Invalid time values in sleep time: {time_str}")
            return None
        
        return time(hour, minute)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse sleep time '{time_str}': {e}")
        return None


def get_sleep_schedule() -> Tuple[Optional[time], Optional[time], bool]:
    """
    Get sleep schedule configuration.
    
    Returns:
        Tuple of (start_time, end_time, enabled)
    """
    enabled = os.getenv("SLEEP_SCHEDULE_ENABLED", "false").lower() == "true"
    if not enabled:
        return (None, None, False)
    
    start_str = os.getenv("SLEEP_SCHEDULE_START", "")
    end_str = os.getenv("SLEEP_SCHEDULE_END", "")
    
    start_time = parse_sleep_time(start_str)
    end_time = parse_sleep_time(end_str)
    
    if not start_time or not end_time:
        logger.warning("Sleep schedule enabled but times not configured properly")
        return (None, None, False)
    
    return (start_time, end_time, True)


def is_in_sleep_hours(current_time: datetime) -> Tuple[bool, str]:
    """
    Check if current time is within sleep schedule.
    
    Args:
        current_time: Current datetime to check
        
    Returns:
        Tuple of (is_sleeping, reason_string)
        
    Examples:
        >>> is_in_sleep_hours(datetime(2026, 1, 29, 3, 0))
        (True, "Sleep schedule active (00:00-07:30)")
        >>> is_in_sleep_hours(datetime(2026, 1, 29, 8, 0))
        (False, "Outside sleep hours")
    """
    start_time, end_time, enabled = get_sleep_schedule()
    
    if not enabled:
        return (False, "Sleep schedule not enabled")
    
    current_time_only = current_time.time()
    
    # Handle midnight-spanning sleep schedule (e.g., 23:00-07:00 or 00:00-07:30)
    if start_time <= end_time:
        # Normal case: 00:00-07:30
        in_sleep = start_time <= current_time_only <= end_time
    else:
        # Midnight-spanning: 23:00-07:00
        in_sleep = current_time_only >= start_time or current_time_only <= end_time
    
    if in_sleep:
        return (True, f"Sleep schedule active ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')})")
    
    return (False, "Outside sleep hours")


def should_suppress_for_sleep(
    category: str,
    name: str,
    status: str,
    current_time: Optional[datetime] = None
) -> Tuple[bool, str]:
    """
    Determine if alert should be suppressed due to sleep schedule.
    
    Sleep Schedule Rules:
    1. If sleep schedule disabled - don't suppress
    2. If outside sleep hours - don't suppress
    3. If critical alerts allowed and SMART/RAID - don't suppress
    4. Otherwise - suppress (including recovery alerts)
    
    Args:
        category: Alert category (service, system, docker, smart, raid)
        name: Service/resource name (plex, jellyfin, cpu, /dev/sda, md0)
        status: New status (OK, WARN, FAIL)
        current_time: Time to check (defaults to now)
        
    Returns:
        Tuple of (should_suppress, reason_string)
        
    Examples:
        >>> should_suppress_for_sleep("service", "jellyfin", "FAIL")
        (True, "Sleep schedule active: Sleep schedule active (00:00-07:30)")
        >>> should_suppress_for_sleep("smart", "/dev/sda", "FAIL")
        (False, "Critical infrastructure alerts allowed during sleep")
    """
    if current_time is None:
        current_time = datetime.now()
    
    # Check if in sleep hours
    is_sleeping, reason = is_in_sleep_hours(current_time)
    
    if not is_sleeping:
        return (False, "Outside sleep hours")
    
    # Check if critical alerts are allowed during sleep
    allow_critical = os.getenv("SLEEP_ALLOW_CRITICAL_ALERTS", "false").lower() == "true"
    
    if allow_critical and category in ['smart', 'raid']:
        return (False, "Critical infrastructure alerts allowed during sleep")
    
    # Suppress everything during sleep (including recovery alerts)
    return (True, f"Sleep schedule active: {reason}")


async def queue_sleep_event(event_data: Dict[str, Any]) -> bool:
    """
    Store event details for morning summary.
    
    Args:
        event_data: Event details including:
            - event_key: Unique event identifier
            - category: Alert category
            - name: Item name
            - prev_status: Previous status
            - new_status: New status
            - message: Alert message
            - details: Additional context
    
    Returns:
        bool: True if successful, False otherwise
    """
    from app.storage import insert_sleep_event
    
    try:
        success = await insert_sleep_event(
            event_key=event_data.get('event_key', ''),
            category=event_data.get('category', ''),
            name=event_data.get('name', ''),
            prev_status=event_data.get('prev_status'),
            new_status=event_data.get('new_status', ''),
            message=event_data.get('message', ''),
            details=event_data.get('details')
        )
        
        if success:
            logger.debug(f"Queued sleep event: {event_data.get('event_key')}")
        else:
            logger.warning(f"Failed to queue sleep event: {event_data.get('event_key')}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error queuing sleep event: {e}", exc_info=True)
        return False


async def generate_morning_summary() -> Optional[Dict[str, Any]]:
    """
    Generate morning summary Discord embed from queued sleep events.
    
    Returns:
        Discord embed dict or None if no events or summary disabled
    """
    from app.storage import get_sleep_events, clear_sleep_events
    
    # Get sleep schedule times for summary period
    start_time, end_time, enabled = get_sleep_schedule()
    
    if not enabled:
        return None
    
    # Check if summary is enabled
    summary_enabled = os.getenv("SLEEP_SUMMARY_ENABLED", "true").lower() == "true"
    if not summary_enabled:
        logger.debug("Morning summary disabled via configuration")
        return None
    
    # Get events from last sleep period
    events = await get_sleep_events()
    
    if not events:
        # No activity overnight - send "quiet night" summary
        embed = {
            "title": "🌅 Good Morning!",
            "description": f"Period: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
            "color": 0x00FF00,  # Green
            "fields": [
                {
                    "name": "✨ Quiet Night",
                    "value": "No events logged during sleep hours",
                    "inline": False
                },
                {
                    "name": "🟢 Current Status",
                    "value": "All systems operational",
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Clear sleep events even though there are none (cleanup)
        await clear_sleep_events()
        
        return embed
    
    # Analyze events
    service_events = [e for e in events if e.get('category') == 'service']
    docker_events = [e for e in events if e.get('category') == 'docker']
    system_events = [e for e in events if e.get('category') == 'system']
    
    # Count ongoing issues (non-OK statuses)
    ongoing_issues = [e for e in events if e.get('new_status') != 'OK']
    
    # Build activity summary
    activity_lines = []
    
    # Group events by time for readability
    event_groups: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        try:
            event_time = datetime.fromisoformat(event['ts'])
            hour = event_time.strftime('%H:%M')
        except:
            hour = "??:??"
        
        if hour not in event_groups:
            event_groups[hour] = []
        event_groups[hour].append(event)
    
    # Format activity log entries
    for hour in sorted(event_groups.keys()):
        hour_events = event_groups[hour]
        for event in hour_events:
            status_emoji = "🟢" if event.get('new_status') == 'OK' else "🔴"
            prev = event.get('prev_status') or '?'
            new = event.get('new_status', '?')
            name = event.get('name', 'unknown')
            activity_lines.append(f"{status_emoji} {hour} - {name}: {prev} → {new}")
    
    # Build embed
    embed = {
        "title": "🌅 Overnight Activity Summary",
        "description": f"Period: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
        "color": 0xFFA500 if ongoing_issues else 0x00FF00,  # Orange if issues, green if all good
        "fields": [
            {
                "name": "📊 Activity Overview",
                "value": (
                    f"• {len(events)} events logged\n"
                    f"• {len(service_events)} service events\n"
                    f"• {len(ongoing_issues)} ongoing issues"
                ),
                "inline": False
            }
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add activity details (limit to 10 most recent)
    if activity_lines:
        activity_text = "\n".join(activity_lines[-10:])
        if len(activity_lines) > 10:
            activity_text = f"*(Showing last 10 of {len(activity_lines)} events)*\n\n" + activity_text
        
        embed["fields"].append({
            "name": "✅ Activity Log",
            "value": activity_text,
            "inline": False
        })
    
    # Add issues section if any
    if ongoing_issues:
        issues_text = "\n".join([
            f"• {e.get('name', 'unknown')}: {e.get('new_status', '?')}"
            for e in ongoing_issues[:5]
        ])
        embed["fields"].append({
            "name": "⚠️ Ongoing Issues",
            "value": issues_text,
            "inline": False
        })
    else:
        embed["fields"].append({
            "name": "🟢 Current Status",
            "value": "All systems operational",
            "inline": False
        })
    
    # Clear sleep events after processing
    await clear_sleep_events()
    logger.info(f"Generated morning summary with {len(events)} events")
    
    return embed
