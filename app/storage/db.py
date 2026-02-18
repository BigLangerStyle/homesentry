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
    CREATE_SLEEP_EVENTS_TABLE,
    CREATE_SLEEP_EVENTS_INDEXES,
    CREATE_SCHEMA_VERSION_TABLE,
    INSERT_SCHEMA_VERSION,
    migrate_to_v030,
    migrate_to_v031,
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
    Runs migrations if needed to update schema to latest version.
    
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
        
        # Create sleep_events table
        await db.execute(CREATE_SLEEP_EVENTS_TABLE)
        await db.executescript(CREATE_SLEEP_EVENTS_INDEXES)
        logger.debug("Created sleep_events table")
        
        # Create schema_version table
        await db.execute(CREATE_SCHEMA_VERSION_TABLE)
        
        # Check current schema version
        cursor = await db.execute("SELECT version FROM schema_version ORDER BY applied_ts DESC LIMIT 1")
        row = await cursor.fetchone()
        current_version = row[0] if row else None
        
        # Run migrations if needed
        if current_version != SCHEMA_VERSION:
            if current_version == "0.1.0" or current_version is None:
                logger.info(f"Migrating database from {current_version or 'unknown'} to v0.3.0")
                await migrate_to_v030(db)
                # Update version to 0.3.0 first
                await db.execute(INSERT_SCHEMA_VERSION, ("0.3.0",))
                current_version = "0.3.0"
            
            if current_version == "0.3.0":
                logger.info(f"Migrating database from v0.3.0 to v0.3.1")
                await migrate_to_v031(db)
            
            # Update schema version to current
            await db.execute(INSERT_SCHEMA_VERSION, (SCHEMA_VERSION,))
            logger.info(f"Database schema updated to v{SCHEMA_VERSION}")
        else:
            logger.debug(f"Database schema already at v{SCHEMA_VERSION}")
        
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
    maintenance_suppressed: bool = False,
    sleep_suppressed: bool = False,
) -> bool:
    """
    Insert or update a state-change event in the database.
    
    Events are uniquely identified by event_key. If an event with the same key
    already exists, it will be replaced (using INSERT OR REPLACE).
    
    Args:
        event_key: Unique event identifier (e.g., 'service_plex', 'disk_/mnt/array')
        new_status: New status (OK, WARN, FAIL)
        message: Human-readable message for Discord notification
        prev_status: Previous status (optional, None for new events)
        maintenance_suppressed: Whether alert was suppressed due to maintenance window
        sleep_suppressed: Whether alert was suppressed due to sleep schedule
    
    Returns:
        bool: True if successful, False otherwise
    
    Examples:
        >>> await insert_event("service_plex", "FAIL", "Plex is unreachable", prev_status="OK")
        >>> await insert_event("service_jellyfin", "FAIL", "Jellyfin down during maintenance",
        ...                   prev_status="OK", maintenance_suppressed=True)
        >>> await insert_event("service_plex", "FAIL", "Plex down during sleep",
        ...                   prev_status="OK", sleep_suppressed=True)
    """
    db = None
    try:
        db = await get_connection()
        await db.execute(
            """
            INSERT OR REPLACE INTO events 
            (event_key, prev_status, new_status, message, notified, notified_ts, 
             maintenance_suppressed, sleep_suppressed)
            VALUES (?, ?, ?, ?, 0, NULL, ?, ?)
            """,
            (event_key, prev_status, new_status, message, 
             1 if maintenance_suppressed else 0, 1 if sleep_suppressed else 0),
        )
        await db.commit()
        
        if sleep_suppressed:
            logger.debug(f"Inserted event (sleep-suppressed): {event_key} ({prev_status} -> {new_status})")
        elif maintenance_suppressed:
            logger.debug(f"Inserted event (maintenance-suppressed): {event_key} ({prev_status} -> {new_status})")
        else:
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


async def insert_sleep_event(
    event_key: str,
    category: str,
    name: str,
    new_status: str,
    message: str,
    prev_status: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Insert event into sleep_events table for morning summary.
    
    Events queued during sleep hours are stored here and cleared after
    the morning summary is generated and sent.
    
    Args:
        event_key: Unique event identifier
        category: Alert category (service, system, docker, smart, raid)
        name: Item name
        new_status: New status (OK, WARN, FAIL)
        message: Human-readable message
        prev_status: Previous status (optional)
        details: Additional context (will be JSON-encoded)
    
    Returns:
        bool: True if successful, False otherwise
    """
    import json
    
    db = None
    try:
        db = await get_connection()
        
        # Convert details dict to JSON string if provided
        details_json = json.dumps(details) if details else None
        
        await db.execute(
            """
            INSERT INTO sleep_events 
            (event_key, category, name, prev_status, new_status, message, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_key, category, name, prev_status, new_status, message, details_json)
        )
        await db.commit()
        logger.debug(f"Inserted sleep event: {event_key} ({prev_status} -> {new_status})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to insert sleep event: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()


async def get_sleep_events() -> List[Dict[str, Any]]:
    """
    Get all sleep events for morning summary generation.
    
    Returns:
        List[Dict[str, Any]]: List of sleep events
    """
    import json
    
    db = None
    try:
        db = await get_connection()
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            """
            SELECT id, ts, event_key, category, name, 
                   prev_status, new_status, message, details_json
            FROM sleep_events
            ORDER BY ts ASC
            """
        )
        rows = await cursor.fetchall()
        
        # Convert rows to dicts and parse JSON details
        events = []
        for row in rows:
            event = dict(row)
            if event.get('details_json'):
                try:
                    event['details'] = json.loads(event['details_json'])
                except (json.JSONDecodeError, ValueError):
                    event['details'] = None
            events.append(event)
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to get sleep events: {e}", exc_info=True)
        return []
    finally:
        if db:
            await db.close()


async def clear_sleep_events() -> bool:
    """
    Clear all sleep events after morning summary has been sent.
    
    Returns:
        bool: True if successful, False otherwise
    """
    db = None
    try:
        db = await get_connection()
        
        await db.execute("DELETE FROM sleep_events")
        await db.commit()
        logger.debug("Cleared all sleep events")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear sleep events: {e}", exc_info=True)
        return False
    finally:
        if db:
            await db.close()


async def get_metric_history(
    metric_name: str,
    hours: int = 24,
    bucket_count: int = 60,
) -> List[Dict[str, Any]]:
    """
    Get bucketed time-series history for a named metric.

    Queries metrics_samples for a given metric name over the past N hours,
    groups rows into evenly-sized time buckets, and returns the average value
    per bucket.  The result is suitable for rendering with Chart.js.

    Args:
        metric_name:  Exact name stored in metrics_samples.name
                      (e.g. "cpu_percent", "memory_percent",
                      "disk_/mnt/Array_free_gb").
        hours:        How far back to look (default 24).
        bucket_count: Number of data points to return (default 60).

    Returns:
        List of dicts with keys ``ts`` (ISO-8601 string, local time)
        and ``value`` (float average, rounded to 2 decimal places).
        Empty list on error or when no data is available.

    Examples:
        >>> rows = await get_metric_history("cpu_percent", hours=24, bucket_count=60)
        >>> rows[0]
        {"ts": "2026-02-16T08:00", "value": 12.34}
    """
    db = None
    try:
        # Calculate the number of minutes per bucket so SQLite can group rows.
        # total_minutes / bucket_count gives minutes-per-bucket; minimum 1.
        total_minutes = hours * 60
        minutes_per_bucket = max(1, total_minutes // bucket_count)

        # Build an ISO-8601 interval string accepted by SQLite's datetime modifier.
        lookback = f"-{hours} hours"

        db = await get_connection()
        db.row_factory = aiosqlite.Row

        # SQLite bucketing: round each ts down to the nearest bucket boundary
        # by integer-dividing the unix timestamp, then multiplying back.
        # strftime('%Y-%m-%dT%H:%M', ...) produces the ISO string Chart.js wants.
        query = """
            SELECT
                strftime(
                    '%Y-%m-%dT%H:%M',
                    datetime(
                        (strftime('%s', ts) / (? * 60)) * (? * 60),
                        'unixepoch', 'localtime'
                    )
                ) AS bucket,
                ROUND(AVG(value_num), 2) AS avg_value
            FROM metrics_samples
            WHERE name = ?
              AND value_num IS NOT NULL
              AND ts >= datetime('now', ?)
            GROUP BY bucket
            ORDER BY bucket ASC
        """

        cursor = await db.execute(
            query,
            (minutes_per_bucket, minutes_per_bucket, metric_name, lookback),
        )
        rows = await cursor.fetchall()

        result = [
            {"ts": row["bucket"], "value": row["avg_value"]}
            for row in rows
            if row["bucket"] is not None and row["avg_value"] is not None
        ]

        logger.debug(
            f"get_metric_history({metric_name!r}, {hours}h, {bucket_count} buckets)"
            f" → {len(result)} points"
        )
        return result

    except Exception as e:
        logger.error(
            f"Failed to get metric history for {metric_name!r}: {e}", exc_info=True
        )
        return []
    finally:
        if db:
            await db.close()


async def get_available_chart_metrics() -> List[Dict[str, Any]]:
    """
    Return the list of numeric metric names that have data in the database.

    Queries distinct names in metrics_samples where value_num is not null
    and data exists in the past 7 days.  Only returns system + disk metrics
    so that Docker/SMART/RAID metrics don't clutter the chart selector.

    Returns:
        List of dicts with keys:
            ``name``  - the raw metric name stored in the DB
            ``label`` - a human-readable display label
            ``unit``  - unit string for the y-axis (e.g. "%" or "GB")

    Examples:
        >>> metrics = await get_available_chart_metrics()
        >>> [m["name"] for m in metrics]
        ["cpu_percent", "memory_percent", "disk_mnt_Array_free_gb"]
    """
    # Fixed catalogue of chartable metrics.
    # RAM is stored as "memory_percent" by the system collector.
    CHARTABLE_METRICS = [
        {"name": "cpu_percent",    "label": "CPU Usage", "unit": "%"},
        {"name": "memory_percent", "label": "RAM Usage", "unit": "%"},
    ]

    # Disk free-GB metrics encode the mount-point in the name.
    # Examples from the system collector:
    #   disk_host_free_gb       -> /host
    #   disk_mnt_Array_free_gb  -> /mnt/Array
    # Strategy: strip "disk_" prefix and "_free_gb" suffix, prepend "/",
    # and replace remaining underscores with "/" to reconstruct the path.
    db = None
    try:
        db = await get_connection()
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT DISTINCT name
            FROM metrics_samples
            WHERE category = 'disk'
              AND name LIKE 'disk_%_free_gb'
              AND value_num IS NOT NULL
              AND ts >= datetime('now', '-7 days')
            ORDER BY name ASC
            """
        )
        rows = await cursor.fetchall()

        known_names = {m["name"] for m in CHARTABLE_METRICS}

        for row in rows:
            raw_name = row["name"]
            if raw_name in known_names:
                continue
            known_names.add(raw_name)

            # Strip "disk_" prefix and "_free_gb" suffix to get the path segment.
            # e.g. "disk_mnt_Array_free_gb" -> "mnt_Array"
            #      "disk_host_free_gb"      -> "host"
            middle = raw_name[len("disk_"):-len("_free_gb")]

            # Reconstruct the filesystem path: prepend "/" and replace "_" with "/".
            # "mnt_Array" -> "/mnt/Array"
            # "host"      -> "/host"
            mount = "/" + middle.replace("_", "/")

            CHARTABLE_METRICS.append({
                "name": raw_name,
                "label": "Disk Free (" + mount + ")",
                "unit": "GB",
            })

        # Filter down to only metrics that actually have data.
        cursor2 = await db.execute(
            """
            SELECT DISTINCT name
            FROM metrics_samples
            WHERE value_num IS NOT NULL
              AND ts >= datetime('now', '-7 days')
            """
        )
        rows2 = await cursor2.fetchall()
        names_with_data = {row["name"] for row in rows2}

        available = [
            m for m in CHARTABLE_METRICS if m["name"] in names_with_data
        ]

        logger.debug("get_available_chart_metrics -> %d metrics with data", len(available))
        return available

    except Exception as e:
        logger.error("Failed to get available chart metrics: %s", e, exc_info=True)
        # Safe fallback so the dashboard doesn't break on DB errors
        return [
            {"name": "cpu_percent",    "label": "CPU Usage", "unit": "%"},
            {"name": "memory_percent", "label": "RAM Usage", "unit": "%"},
        ]
    finally:
        if db:
            await db.close()


async def delete_old_metrics(retention_days: int) -> tuple[int, int]:
    """
    Delete metrics and service status rows older than retention_days days.

    This is the nightly cleanup function that prevents unbounded table growth.
    Both metrics_samples and service_status are pruned; the events table is
    intentionally left alone because it only grows on state changes and is
    tiny by comparison.

    Args:
        retention_days: Number of days of history to keep.  Must be > 0.

    Returns:
        Tuple of (metrics_deleted, service_status_deleted) row counts.
    """
    db = None
    try:
        db = await get_connection()

        param = (str(retention_days),)

        cursor = await db.execute(
            "DELETE FROM metrics_samples WHERE ts < datetime('now', '-' || ? || ' days')",
            param,
        )
        metrics_deleted: int = cursor.rowcount

        cursor2 = await db.execute(
            "DELETE FROM service_status WHERE ts < datetime('now', '-' || ? || ' days')",
            param,
        )
        service_deleted: int = cursor2.rowcount

        await db.commit()

        logger.info(
            "Data retention cleanup: removed %d metrics_samples rows and "
            "%d service_status rows older than %d days",
            metrics_deleted,
            service_deleted,
            retention_days,
        )
        return metrics_deleted, service_deleted

    except Exception as e:
        logger.error("Failed to run data retention cleanup: %s", e, exc_info=True)
        return 0, 0
    finally:
        if db:
            await db.close()
