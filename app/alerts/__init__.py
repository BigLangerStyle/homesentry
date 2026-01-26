"""
Alerts module - Notification system for HomeSentry

This module provides Discord webhook integration and intelligent alert rules:
- discord.py - Discord webhook integration and message formatting
- rules.py - Alert state-change logic and cooldown management
"""

from .discord import (
    send_discord_webhook,
    send_alert_async,
    format_service_alert,
    format_system_alert,
    format_disk_alert,
    get_status_color,
    get_status_emoji,
)

from .rules import (
    check_state_change,
    process_alert,
    generate_event_key,
    should_alert,
)

__all__ = [
    # Discord webhook functions
    "send_discord_webhook",
    "send_alert_async",
    "format_service_alert",
    "format_system_alert",
    "format_disk_alert",
    "get_status_color",
    "get_status_emoji",
    # Alert rules functions
    "check_state_change",
    "process_alert",
    "generate_event_key",
    "should_alert",
]

