"""
Database storage modules for persisting metrics and events.

This module provides database operations for HomeSentry:
- init_database() - Initialize database tables
- insert_metric_sample() - Insert metric data
- insert_service_status() - Insert service health check
- insert_event() - Insert state-change event
- get_latest_metrics() - Query recent metrics
- get_latest_events() - Query recent events
- get_latest_service_status() - Query recent service checks
- get_latest_event_by_key() - Query specific event for state tracking
- update_event_notified() - Mark event as notified for cooldown tracking
- insert_sleep_event() - Insert event into sleep queue
- get_sleep_events() - Get all queued sleep events
- clear_sleep_events() - Clear sleep events after summary sent
"""

from .db import (
    init_database,
    get_connection,
    insert_metric_sample,
    insert_service_status,
    insert_event,
    get_latest_metrics,
    get_latest_events,
    get_latest_service_status,
    get_latest_event_by_key,
    update_event_notified,
    insert_sleep_event,
    get_sleep_events,
    clear_sleep_events,
)

__all__ = [
    "init_database",
    "get_connection",
    "insert_metric_sample",
    "insert_service_status",
    "insert_event",
    "get_latest_metrics",
    "get_latest_events",
    "get_latest_service_status",
    "get_latest_event_by_key",
    "update_event_notified",
    "insert_sleep_event",
    "get_sleep_events",
    "clear_sleep_events",
]
