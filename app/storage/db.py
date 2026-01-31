"""
Database operations for HomeSentry

This module provides async database connection management and helper functions
for inserting and querying metrics, service status, and events.

All database operations are async and use aiosqlite for SQLite access.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import aiosqlite

from .models import (
    SCHEMA_VERSION,
    CREATE_METRICS_SAMPLES_TABLE,
    CREATE_METRICS_INDEXES,
    CREATE_SERVICE_STATUS_TABLE,
    CREATE_SERVICE_INDEXES,
    CREATE_EVENTS_TABLE,
    CREATE_EVENTS_INDEXES,
    CREATE_SCHEMA_VERSION_TABLE,
    INSERT_SCHEMA_VERSION,
)

logger = logging.getLogger(__name__)


async def get_connection() -> aiosqlite.Connection:
    """
    Get database connection.
    
    Creates the database file and parent directory if they don't exist.
    
    Returns:
        aiosqlite.Connection: Database connection
    """
    db_path = os.getenv("DATABASE_PATH", "data/homesentry.db")
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    return await aiosqlite.connect(db_path)


async def init_database() -> bool:
    """
    Initialize database by creating all tables and indexes.
    
    This function is idempotent - it's safe to call multiple times.
    Tables are created with IF NOT EXISTS, so existing tables won't be affected.
    
    Returns:
        bool: True if successful, False otherwise
    """
    db = None
    try:
        db = await get_connection()
        
        # Create metrics_samples table
        await db.execute(CREATE_METRICS_SAMPLES_TABLE)
        await db.executescript(CREATE_METRICS_INDEXES)
        logger.debug("Created metrics_samples table")
        
        # Create service_status table
        await db.execute(CREATE_SERVICE_STATUS_TABLE)
        await db.executescript(CREATE_SERVICE_INDEXES)
        logger.debug("Created service_status table")
        
        # Create events table
        await db.execute(CREATE_EVENTS_TABLE)
        await db.executescript(CREATE_EVENTS_INDEXES)
        logger.debug("Created events table")
        
        # Create schema_version table
        await db.execute(CREATE_SCHEMA_VERSION_TABLE)
        await db.execute(INSERT_SCHEMA_VERSION, (SCHEMA_VERSION,))
        logger.debug(f"Initialized schema version: {SCHEMA_VERSION}")
        
        await db.commit()
        logger.info(f"Database initialized successfully (schema v{SCHEMA_VERSION})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()


async def insert_metric_sample(
    category: str,
    name: str,
    value_num: Optional[float] = None,
    value_text: Optional[str] = None,
    status: str = "OK",
    details_json: Optional[str] = None,
) -> bool:
    """
    Insert a metric sample into the database.
    
    Args:
        category: Metric category (system, disk, smart, docker, raid)
        name: Metric name (cpu_percent, disk_/mnt/Array_free_gb, etc.)
        value_num: Numeric value (optional)
        value_text: Text value (optional)
        status: Status (OK, WARN, FAIL)
        details_json: Additional data as JSON string (optional)
    
    Returns:
        bool: True if successful, False otherwise
    
    Examples:
        >>> await insert_metric_sample("system", "cpu_percent", value_num=45.2, status="OK")
        >>> await insert_metric_sample("disk", "disk_/mnt/Array_free_gb", value_num=1250.5)
        >>> await insert_metric_sample("smart", "drive_/dev/sda_health", value_text="PASSED")
    """
    db = None
    try:
        db = await get_connection()
        await db.execute(
            """
            INSERT INTO metrics_samples 
            (category, name, value_num, value_text, status, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (category, name, value_num, value_text, status, details_json),
        )
        await db.commit()
        logger.debug(f"Inserted metric: {category}/{name} = {value_num or value_text}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to insert metric sample: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()


async def insert_service_status(
    service: str,
    status: str,
    response_ms: Optional[float] = None,
    http_code: Optional[int] = None,
    details_json: Optional[str] = None,
) -> bool:
    """
    Insert a service status check into the database.
    
    Args:
        service: Service name (plex, jellyfin, pihole, etc.)
        status: Status (OK, WARN, FAIL)
        response_ms: Response time in milliseconds (optional)
        http_code: HTTP status code (200, 500, etc.) (optional)
        details_json: Additional data as JSON string (optional)
    
    Returns:
        bool: True if successful, False otherwise
    
    Examples:
        >>> await insert_service_status("plex", "OK", response_ms=45.2, http_code=200)
        >>> await insert_service_status("jellyfin", "FAIL", http_code=500, 
        ...                             details_json='{"error": "Connection timeout"}')
    """
    db = None
    try:
        db = await get_connection()
        await db.execute(
            """
            INSERT INTO service_status 
            (service, status, response_ms, http_code, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (service, status, response_ms, http_code, details_json),
        )
        await db.commit()
        logger.debug(f"Inserted service status: {service} = {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to insert service status: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()


async def insert_event(
    event_key: str,
    new_status: str,
    message: str,
    prev_status: Optional[str] = None,
) -> bool:
    """
    Insert or update a state-change event in the database.
    
    Events are uniquely identified by event_key. If an event with the same key
    already exists, it will be replaced (using INSERT OR REPLACE).
    
    Args:
        event_key: Unique event identifier (e.g., 'plex_down', 'disk_/mnt/Array_critical')
        new_status: New status (OK, WARN, FAIL)
        message: Human-readable message for Discord notification
        prev_status: Previous status (optional, None for new events)
    
    Returns:
        bool: True if successful, False otherwise
    
    Examples:
        >>> await insert_event("plex_down", "FAIL", "Plex is unreachable", prev_status="OK")
        >>> await insert_event("disk_/mnt/Array_warn", "WARN", 
        ...                   "Disk usage > 85%", prev_status="OK")
    """
    db = None
    try:
        db = await get_connection()
        await db.execute(
            """
            INSERT OR REPLACE INTO events 
            (event_key, prev_status, new_status, message, notified, notified_ts)
            VALUES (?, ?, ?, ?, 0, NULL)
            """,
            (event_key, prev_status, new_status, message),
        )
        await db.commit()
        logger.debug(f"Inserted event: {event_key} ({prev_status} -> {new_status})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to insert event: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()


async def get_latest_metrics(
    category: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get latest metric samples from the database.
    
    Args:
        category: Filter by category (optional, returns all if None)
        limit: Maximum number of rows to return (default: 100)
    
    Returns:
        List[Dict[str, Any]]: List of metric samples as dictionaries
    
    Examples:
        >>> metrics = await get_latest_metrics(category="system", limit=10)
        >>> for metric in metrics:
        ...     print(f"{metric['name']}: {metric['value_num']}")
    """
    db = None
    try:
        db = await get_connection()
        db.row_factory = aiosqlite.Row
        
        if category:
            query = """
                SELECT * FROM metrics_samples 
                WHERE category = ?
                ORDER BY ts DESC 
                LIMIT ?
            """
            cursor = await db.execute(query, (category, limit))
        else:
            query = """
                SELECT * FROM metrics_samples 
                ORDER BY ts DESC 
                LIMIT ?
            """
            cursor = await db.execute(query, (limit,))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get latest metrics: {e}", exc_info=True)
        return []
    finally:
        if db:
            await db.close()


async def get_latest_events(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get latest events from the database.
    
    Args:
        limit: Maximum number of rows to return (default: 50)
    
    Returns:
        List[Dict[str, Any]]: List of events as dictionaries
    
    Examples:
        >>> events = await get_latest_events(limit=10)
        >>> for event in events:
        ...     print(f"{event['event_key']}: {event['message']}")
    """
    db = None
    try:
        db = await get_connection()
        db.row_factory = aiosqlite.Row
        
        query = """
            SELECT * FROM events 
            ORDER BY ts DESC 
            LIMIT ?
        """
        cursor = await db.execute(query, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get latest events: {e}", exc_info=True)
        return []
    finally:
        if db:
            await db.close()


async def get_latest_service_status(
    service: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get latest service status checks from the database.
    
    Args:
        service: Filter by service name (optional, returns all if None)
        limit: Maximum number of rows to return (default: 100)
    
    Returns:
        List[Dict[str, Any]]: List of service status checks as dictionaries
    
    Examples:
        >>> statuses = await get_latest_service_status(service="plex", limit=10)
        >>> for status in statuses:
        ...     print(f"{status['service']}: {status['status']} ({status['http_code']})")
    """
    db = None
    try:
        db = await get_connection()
        db.row_factory = aiosqlite.Row
        
        if service:
            query = """
                SELECT * FROM service_status 
                WHERE service = ?
                ORDER BY ts DESC 
                LIMIT ?
            """
            cursor = await db.execute(query, (service, limit))
        else:
            query = """
                SELECT * FROM service_status 
                ORDER BY ts DESC 
                LIMIT ?
            """
            cursor = await db.execute(query, (limit,))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get latest service status: {e}", exc_info=True)
        return []
    finally:
        if db:
            await db.close()


async def get_latest_event_by_key(event_key: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent event for a given event key.
    
    This function is used by the alert rules engine to check previous state
    and determine if an alert should be sent.
    
    Args:
        event_key: Unique event identifier (e.g., 'service_plex', 'disk_/mnt/array')
    
    Returns:
        Dict with event details if found, None otherwise
        
    Example:
        >>> event = await get_latest_event_by_key("service_plex")
        >>> if event:
        ...     print(f"Last status: {event['new_status']}")
        ...     print(f"Notified: {event['notified']}")
    """
    db = None
    try:
        db = await get_connection()
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            """
            SELECT event_key, prev_status, new_status, message, 
                   notified, notified_ts, ts
            FROM events
            WHERE event_key = ?
            ORDER BY ts DESC
            LIMIT 1
            """,
            (event_key,)
        )
        row = await cursor.fetchone()
        
        if row:
            return dict(row)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get latest event for {event_key}: {e}", exc_info=True)
        return None
    finally:
        if db:
            await db.close()


async def update_event_notified(event_key: str) -> bool:
    """
    Mark the most recent event as notified.
    
    This function is called after successfully sending an alert to track
    when notifications were sent for cooldown purposes.
    
    Args:
        event_key: Unique event identifier
    
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        >>> success = await update_event_notified("service_plex")
    """
    db = None
    try:
        db = await get_connection()
        
        await db.execute(
            """
            UPDATE events
            SET notified = 1, notified_ts = CURRENT_TIMESTAMP
            WHERE event_key = ? 
            AND ts = (
                SELECT MAX(ts) FROM events WHERE event_key = ?
            )
            AND notified = 0
            """,
            (event_key, event_key)
        )
        await db.commit()
        logger.debug(f"Marked event {event_key} as notified")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update event notification status for {event_key}: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()
