"""
Discord webhook integration for HomeSentry alerts

This module provides functions to send formatted alerts to Discord via webhooks.
Alerts are sent as rich embeds with color-coding, status indicators, and relevant
details about service health, system metrics, and disk space.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

# Discord embed colors (RGB as integer)
COLOR_OK = 65280      # Green (#00FF00)
COLOR_WARN = 16776960  # Yellow (#FFFF00)
COLOR_FAIL = 16711680  # Red (#FF0000)

# Status emoji indicators
STATUS_EMOJI = {
    "OK": "🟢",
    "WARN": "🟡",
    "FAIL": "🔴"
}


def get_status_color(status: str) -> int:
    """
    Get Discord embed color for status.
    
    Args:
        status: Status string (OK, WARN, FAIL)
    
    Returns:
        int: Discord color code
    """
    colors = {
        "OK": COLOR_OK,
        "WARN": COLOR_WARN,
        "FAIL": COLOR_FAIL
    }
    return colors.get(status, COLOR_WARN)


def get_status_emoji(status: str) -> str:
    """
    Get emoji indicator for status.
    
    Args:
        status: Status string (OK, WARN, FAIL)
    
    Returns:
        str: Emoji character
    """
    return STATUS_EMOJI.get(status, "⚪")


def send_discord_webhook(webhook_url: str, embed: Dict[str, Any]) -> bool:
    """
    Send message to Discord webhook (synchronous).
    
    This function sends a Discord embed to the specified webhook URL.
    It includes error handling and logging for successful and failed deliveries.
    
    Args:
        webhook_url: Discord webhook URL
        embed: Discord embed dictionary
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        >>> embed = format_service_alert("plex", None, "FAIL", {"error": "Connection timeout"})
        >>> success = send_discord_webhook("https://discord.com/api/webhooks/...", embed)
    """
    payload = {
        "username": "HomeSentry",
        "embeds": [embed]
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Discord alert sent successfully: {embed.get('title', 'Untitled')}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False


async def send_alert_async(webhook_url: str, embed: Dict[str, Any]) -> bool:
    """
    Send Discord alert asynchronously with rate limit protection.
    
    This function wraps the synchronous webhook call in an async executor
    to prevent blocking the main event loop. It includes a 1-second delay
    to avoid hitting Discord's rate limit (30 requests per 60 seconds).
    
    Args:
        webhook_url: Discord webhook URL
        embed: Discord embed dictionary
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Add 1-second delay to prevent rate limiting when multiple alerts fire
    # Discord allows 30 requests/60s, so 1s delay keeps us well under the limit
    await asyncio.sleep(1)
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        send_discord_webhook,
        webhook_url,
        embed
    )
    return result


def format_service_alert(
    service_name: str,
    prev_status: Optional[str],
    new_status: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format service health check alert for Discord.
    
    Creates a rich Discord embed with service status information including
    response time, HTTP codes, and error messages.
    
    Args:
        service_name: Service name (e.g., 'plex', 'jellyfin')
        prev_status: Previous status (OK/WARN/FAIL) or None for first detection
        new_status: New status (OK/WARN/FAIL)
        details: Additional details dictionary with keys:
            - url: Service URL
            - response_ms: Response time in milliseconds
            - http_code: HTTP status code
            - error: Error message (if any)
    
    Returns:
        Dict[str, Any]: Discord embed dictionary
    
    Example:
        >>> embed = format_service_alert(
        ...     "plex", "OK", "FAIL",
        ...     {"url": "http://192.168.1.8:32400", "error": "Connection timeout"}
        ... )
    """
    emoji = get_status_emoji(new_status)
    service_title = service_name.title()
    
    # Determine title based on status
    if new_status == "FAIL":
        title = f"{emoji} Service Down: {service_title}"
        description = f"{service_title} is unreachable"
    elif new_status == "WARN":
        title = f"{emoji} Service Warning: {service_title}"
        description = f"{service_title} is responding slowly or with errors"
    else:  # OK - recovery
        title = f"{emoji} Service Recovered: {service_title}"
        description = f"{service_title} is responding normally"
    
    # Build fields
    fields = []
    
    # Status transition
    if prev_status:
        status_text = f"{prev_status} → {new_status}"
    else:
        status_text = f"First detection: {new_status}"
    
    fields.append({
        "name": "Status",
        "value": status_text,
        "inline": True
    })
    
    # Response time
    if details.get("response_ms") is not None:
        fields.append({
            "name": "Response Time",
            "value": f"{details['response_ms']:.0f}ms",
            "inline": True
        })
    
    # HTTP code
    if details.get("http_code"):
        fields.append({
            "name": "HTTP Code",
            "value": str(details["http_code"]),
            "inline": True
        })
    
    # URL
    if details.get("url"):
        fields.append({
            "name": "URL",
            "value": details["url"],
            "inline": False
        })
    
    # Error message
    if details.get("error"):
        fields.append({
            "name": "Error",
            "value": details["error"],
            "inline": False
        })
    
    embed = {
        "title": title,
        "description": description,
        "color": get_status_color(new_status),
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "HomeSentry v0.1.0"
        }
    }
    
    return embed


def format_system_alert(
    metric_name: str,
    prev_status: Optional[str],
    new_status: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format system metric alert for Discord.
    
    Creates a rich Discord embed for system metrics like CPU, memory, or load average.
    
    Args:
        metric_name: Metric name (e.g., 'cpu', 'memory', 'load_avg')
        prev_status: Previous status or None
        new_status: New status (OK/WARN/FAIL)
        details: Additional details dictionary with keys:
            - value: Current metric value
            - threshold: Threshold that triggered the alert
            - unit: Unit of measurement (%, GB, etc.)
            - message: Human-readable message
    
    Returns:
        Dict[str, Any]: Discord embed dictionary
    """
    emoji = get_status_emoji(new_status)
    metric_title = metric_name.replace("_", " ").title()
    
    # Determine title
    if new_status == "FAIL":
        title = f"{emoji} Critical: {metric_title}"
    elif new_status == "WARN":
        title = f"{emoji} Warning: {metric_title}"
    else:
        title = f"{emoji} Recovered: {metric_title}"
    
    description = details.get("message", f"{metric_title} status changed")
    
    # Build fields
    fields = []
    
    # Status transition
    if prev_status:
        status_text = f"{prev_status} → {new_status}"
    else:
        status_text = f"First detection: {new_status}"
    
    fields.append({
        "name": "Status",
        "value": status_text,
        "inline": True
    })
    
    # Current value
    if details.get("value") is not None:
        unit = details.get("unit", "")
        fields.append({
            "name": "Current Value",
            "value": f"{details['value']}{unit}",
            "inline": True
        })
    
    # Threshold
    if details.get("threshold") is not None:
        unit = details.get("unit", "")
        fields.append({
            "name": "Threshold",
            "value": f"{details['threshold']}{unit}",
            "inline": True
        })
    
    embed = {
        "title": title,
        "description": description,
        "color": get_status_color(new_status),
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "HomeSentry v0.1.0"
        }
    }
    
    return embed


def format_disk_alert(
    mountpoint: str,
    prev_status: Optional[str],
    new_status: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format disk space alert for Discord.
    
    Creates a rich Discord embed for disk space warnings and critical alerts.
    
    Args:
        mountpoint: Disk mountpoint (e.g., '/mnt/Array', '/')
        prev_status: Previous status or None
        new_status: New status (OK/WARN/FAIL)
        details: Additional details dictionary with keys:
            - free_gb: Free space in GB
            - total_gb: Total space in GB
            - percent_used: Percentage used
            - threshold_gb: Free space threshold in GB
            - threshold_pct: Percentage threshold
    
    Returns:
        Dict[str, Any]: Discord embed dictionary
    """
    emoji = get_status_emoji(new_status)
    
    # Determine title
    if new_status == "FAIL":
        title = f"{emoji} Critical Disk Space: {mountpoint}"
        description = "Disk space is critically low"
    elif new_status == "WARN":
        title = f"{emoji} Low Disk Space: {mountpoint}"
        description = "Disk usage is approaching critical levels"
    else:
        title = f"{emoji} Disk Space Recovered: {mountpoint}"
        description = "Disk space has returned to normal levels"
    
    # Build fields
    fields = []
    
    # Status transition
    if prev_status:
        status_text = f"{prev_status} → {new_status}"
    else:
        status_text = f"First detection: {new_status}"
    
    fields.append({
        "name": "Status",
        "value": status_text,
        "inline": True
    })
    
    # Free space
    if details.get("free_gb") is not None:
        percent_free = 100 - details.get("percent_used", 0)
        fields.append({
            "name": "Free Space",
            "value": f"{details['free_gb']:.1f} GB ({percent_free:.0f}%)",
            "inline": True
        })
    
    # Total capacity
    if details.get("total_gb"):
        fields.append({
            "name": "Total Capacity",
            "value": f"{details['total_gb']:.1f} GB",
            "inline": True
        })
    
    # Threshold information
    threshold_parts = []
    if details.get("threshold_gb"):
        threshold_parts.append(f"{details['threshold_gb']} GB")
    if details.get("threshold_pct"):
        threshold_parts.append(f"{details['threshold_pct']}%")
    
    if threshold_parts:
        fields.append({
            "name": "Threshold",
            "value": " or ".join(threshold_parts),
            "inline": False
        })
    
    embed = {
        "title": title,
        "description": description,
        "color": get_status_color(new_status),
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "HomeSentry v0.1.0"
        }
    }
    
    return embed
