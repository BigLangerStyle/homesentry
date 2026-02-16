"""
Maintenance Window Management for HomeSentry

Handles time-based alert suppression during scheduled maintenance windows.
Supports per-service maintenance schedules and global maintenance windows
to prevent alert fatigue during planned downtime events.

Configuration via environment variables:
    - JELLYFIN_MAINTENANCE_WINDOW=03:00-03:15
    - GLOBAL_MAINTENANCE_WINDOW=05:00-05:15
    - JELLYFIN_MAINTENANCE_DAYS=0,1,2,3,4,5,6 (optional, 0=Monday, 6=Sunday)
"""
import logging
import os
from datetime import datetime, time
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


def parse_maintenance_window(window_str: str) -> Optional[Tuple[time, time]]:
    """
    Parse maintenance window string in format "HH:MM-HH:MM".
    
    Supports 24-hour time format and handles midnight-spanning windows
    (e.g., "23:45-00:15").
    
    Args:
        window_str: String like "03:00-03:15" or "23:45-00:15"
        
    Returns:
        Tuple of (start_time, end_time) or None if invalid
        
    Examples:
        >>> parse_maintenance_window("03:00-03:15")
        (datetime.time(3, 0), datetime.time(3, 15))
        >>> parse_maintenance_window("23:45-00:15")
        (datetime.time(23, 45), datetime.time(0, 15))
        >>> parse_maintenance_window("invalid")
        None
    """
    if not window_str or not isinstance(window_str, str):
        return None
    
    try:
        # Split on hyphen
        parts = window_str.strip().split('-')
        if len(parts) != 2:
            logger.warning(f"Invalid maintenance window format (expected HH:MM-HH:MM): {window_str}")
            return None
        
        # Parse start and end times
        start_str, end_str = parts
        start_parts = start_str.strip().split(':')
        end_parts = end_str.strip().split(':')
        
        if len(start_parts) != 2 or len(end_parts) != 2:
            logger.warning(f"Invalid time format in maintenance window: {window_str}")
            return None
        
        start_hour, start_min = int(start_parts[0]), int(start_parts[1])
        end_hour, end_min = int(end_parts[0]), int(end_parts[1])
        
        # Validate ranges
        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
            logger.warning(f"Invalid start time in maintenance window: {window_str}")
            return None
        if not (0 <= end_hour <= 23 and 0 <= end_min <= 59):
            logger.warning(f"Invalid end time in maintenance window: {window_str}")
            return None
        
        start_time = time(start_hour, start_min)
        end_time = time(end_hour, end_min)
        
        return (start_time, end_time)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse maintenance window '{window_str}': {e}")
        return None


def parse_maintenance_days(days_str: str) -> List[int]:
    """
    Parse day-of-week filter string.
    
    Args:
        days_str: Comma-separated day numbers (0=Monday, 6=Sunday)
                 Example: "0,1,2,3,4,5,6" or "6" or ""
        
    Returns:
        List of day integers, or [0,1,2,3,4,5,6] if empty (all days)
        
    Examples:
        >>> parse_maintenance_days("0,1,2,3,4,5,6")
        [0, 1, 2, 3, 4, 5, 6]
        >>> parse_maintenance_days("6")
        [6]
        >>> parse_maintenance_days("")
        [0, 1, 2, 3, 4, 5, 6]
    """
    if not days_str or not isinstance(days_str, str):
        # Empty or invalid - default to all days
        return [0, 1, 2, 3, 4, 5, 6]
    
    try:
        days = [int(d.strip()) for d in days_str.split(',') if d.strip()]
        # Validate all days are in range 0-6
        valid_days = [d for d in days if 0 <= d <= 6]
        
        if len(valid_days) != len(days):
            logger.warning(f"Some invalid day numbers in maintenance days: {days_str}")
        
        if not valid_days:
            logger.warning(f"No valid days in maintenance days '{days_str}', using all days")
            return [0, 1, 2, 3, 4, 5, 6]
        
        return sorted(valid_days)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse maintenance days '{days_str}': {e}")
        return [0, 1, 2, 3, 4, 5, 6]


def is_time_in_window(
    current_time: time,
    start_time: time,
    end_time: time
) -> bool:
    """
    Check if current time falls within maintenance window.
    
    Handles midnight-spanning windows correctly (e.g., 23:45-00:15).
    
    Args:
        current_time: Time to check
        start_time: Window start time
        end_time: Window end time
        
    Returns:
        True if current_time is within the window, False otherwise
        
    Examples:
        >>> is_time_in_window(time(3, 5), time(3, 0), time(3, 15))
        True
        >>> is_time_in_window(time(3, 20), time(3, 0), time(3, 15))
        False
        >>> is_time_in_window(time(0, 5), time(23, 45), time(0, 15))
        True
    """
    if start_time <= end_time:
        # Normal window (e.g., 03:00-03:15)
        return start_time <= current_time <= end_time
    else:
        # Midnight-spanning window (e.g., 23:45-00:15)
        return current_time >= start_time or current_time <= end_time


def get_maintenance_config(service_name: str) -> Tuple[Optional[Tuple[time, time]], List[int]]:
    """
    Get maintenance window configuration for a service.
    
    Checks both service-specific and global maintenance window settings.
    Service-specific settings take precedence over global settings.
    
    Args:
        service_name: Service name (e.g., "jellyfin", "homeassistant", "plex")
        
    Returns:
        Tuple of (maintenance_window, allowed_days) or (None, []) if not configured
        
    Examples:
        >>> os.environ["JELLYFIN_MAINTENANCE_WINDOW"] = "03:00-03:15"
        >>> os.environ["JELLYFIN_MAINTENANCE_DAYS"] = "0,1,2,3,4,5,6"
        >>> get_maintenance_config("jellyfin")
        ((datetime.time(3, 0), datetime.time(3, 15)), [0, 1, 2, 3, 4, 5, 6])
    """
    # Normalize service name to uppercase for env var lookup
    service_upper = service_name.upper()
    
    # Check service-specific maintenance window first
    window_key = f"{service_upper}_MAINTENANCE_WINDOW"
    days_key = f"{service_upper}_MAINTENANCE_DAYS"
    
    window_str = os.getenv(window_key, "").strip()
    
    if window_str:
        # Service-specific window configured
        window = parse_maintenance_window(window_str)
        if window:
            days_str = os.getenv(days_key, "")
            days = parse_maintenance_days(days_str)
            logger.debug(
                f"Service-specific maintenance window for {service_name}: "
                f"{window[0]}-{window[1]} on days {days}"
            )
            return (window, days)
    
    # Check global maintenance window
    global_window_str = os.getenv("GLOBAL_MAINTENANCE_WINDOW", "").strip()
    
    if global_window_str:
        global_window = parse_maintenance_window(global_window_str)
        if global_window:
            global_days_str = os.getenv("GLOBAL_MAINTENANCE_DAYS", "")
            global_days = parse_maintenance_days(global_days_str)
            logger.debug(
                f"Global maintenance window applies to {service_name}: "
                f"{global_window[0]}-{global_window[1]} on days {global_days}"
            )
            return (global_window, global_days)
    
    # No maintenance window configured
    return (None, [])


def is_in_maintenance_window(
    service_name: str,
    current_time: datetime
) -> Tuple[bool, str]:
    """
    Check if service is currently in a maintenance window.
    
    This is the main function used by the alert processing system.
    It checks both service-specific and global maintenance windows,
    validates day-of-week filtering, and returns a detailed reason string.
    
    Args:
        service_name: Service name (e.g., "jellyfin", "homeassistant")
        current_time: Current datetime to check
        
    Returns:
        Tuple of (is_maintenance, reason_string)
        
    Examples:
        >>> # Service in maintenance window at 3:05 AM on Monday
        >>> is_in_maintenance_window("jellyfin", datetime(2026, 1, 27, 3, 5))
        (True, "Service-specific window 03:00-03:15 on Monday")
        
        >>> # Service not in maintenance window
        >>> is_in_maintenance_window("jellyfin", datetime(2026, 1, 27, 4, 0))
        (False, "Not in maintenance window")
    """
    window, allowed_days = get_maintenance_config(service_name)
    
    if not window:
        return (False, "Not in maintenance window")
    
    start_time, end_time = window
    current_time_only = current_time.time()
    current_day = current_time.weekday()  # 0=Monday, 6=Sunday
    
    # Check if current day is allowed
    if current_day not in allowed_days:
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return (
            False,
            f"Maintenance window configured but not for {day_names[current_day]}"
        )
    
    # Check if current time is within window
    if is_time_in_window(current_time_only, start_time, end_time):
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        window_source = "Service-specific" if os.getenv(f"{service_name.upper()}_MAINTENANCE_WINDOW") else "Global"
        return (
            True,
            f"{window_source} window {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} "
            f"on {day_names[current_day]}"
        )
    
    return (False, "Not in maintenance window")


def should_suppress_alert(
    category: str,
    name: str,
    status: str,
    current_time: Optional[datetime] = None
) -> Tuple[bool, str]:
    """
    Determine if alert should be suppressed based on maintenance windows.
    
    Alert Suppression Rules:
    1. Critical infrastructure (SMART, RAID) - NEVER suppress
    2. Recovery alerts (any status → OK) - NEVER suppress
    3. During maintenance window - SUPPRESS (log but don't send to Discord)
    
    Args:
        category: Alert category (service, system, docker, smart, raid)
        name: Service/resource name (plex, jellyfin, cpu, /dev/sda, md0)
        status: New status (OK, WARN, FAIL)
        current_time: Time to check (defaults to now)
        
    Returns:
        Tuple of (should_suppress, reason_string)
        
    Examples:
        >>> # Service down during maintenance window - SUPPRESS
        >>> should_suppress_alert("service", "jellyfin", "FAIL")
        (True, "In maintenance window: Service-specific window 03:00-03:15")
        
        >>> # Recovery alert - NEVER suppress
        >>> should_suppress_alert("service", "jellyfin", "OK")
        (False, "Recovery alerts not suppressed")
        
        >>> # SMART failure - NEVER suppress (critical infrastructure)
        >>> should_suppress_alert("smart", "/dev/sda", "FAIL")
        (False, "Critical infrastructure alerts not suppressed")
    """
    if current_time is None:
        current_time = datetime.now()
    
    # Rule 1: Critical infrastructure (SMART, RAID) - never suppress
    if category in ['smart', 'raid']:
        return (False, "Critical infrastructure alerts not suppressed")
    
    # Rule 2: Recovery alerts (→ OK) - never suppress
    if status == 'OK':
        return (False, "Recovery alerts not suppressed")
    
    # Rule 3: Check if in maintenance window
    is_maintenance, reason = is_in_maintenance_window(name, current_time)
    
    if is_maintenance:
        return (True, f"In maintenance window: {reason}")
    
    return (False, "Not in maintenance window")
