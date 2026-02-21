"""
Database schema definitions for HomeSentry

This module contains SQL schema definitions for all database tables.
Tables are designed to store metrics, service status, and state-change events.

Schema Version: 1.0.0
"""

SCHEMA_VERSION = "1.0.0"

# =============================================================================
# Metrics Samples Table
# =============================================================================
# Stores time-series metrics from all collectors (system, disk, SMART, etc.)
# Each row represents a single metric sample at a point in time.
#
# Examples:
#   - System: category='system', name='cpu_percent', value_num=45.2
#   - Disk: category='disk', name='disk_/mnt/Array_free_gb', value_num=1250.5
#   - SMART: category='smart', name='drive_/dev/sda_health', value_text='PASSED'

CREATE_METRICS_SAMPLES_TABLE = """
CREATE TABLE IF NOT EXISTS metrics_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    value_num REAL,
    value_text TEXT,
    status TEXT NOT NULL,
    details_json TEXT
);
"""

CREATE_METRICS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics_samples(ts);
CREATE INDEX IF NOT EXISTS idx_metrics_category ON metrics_samples(category);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics_samples(name);
"""

# =============================================================================
# Service Status Table
# =============================================================================
# Stores HTTP health check results for monitored services (Plex, Jellyfin, etc.)
# Each row represents a single health check attempt.
#
# Examples:
#   - service='plex', status='OK', response_ms=45.2, http_code=200
#   - service='jellyfin', status='FAIL', http_code=500, details_json='{"error": "Connection timeout"}'

CREATE_SERVICE_STATUS_TABLE = """
CREATE TABLE IF NOT EXISTS service_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    service TEXT NOT NULL,
    status TEXT NOT NULL,
    response_ms REAL,
    http_code INTEGER,
    details_json TEXT
);
"""

CREATE_SERVICE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_service_ts ON service_status(ts);
CREATE INDEX IF NOT EXISTS idx_service_name ON service_status(service);
"""

# =============================================================================
# Events Table
# =============================================================================
# Tracks state changes for alerting logic (prevents duplicate alerts)
# Each row represents a state change that may require notification.
#
# The event_key is unique and identifies the specific thing being monitored.
# When a state changes (OK -> WARN, WARN -> FAIL, etc.), a new event is created.
# This allows the alerting system to track what has been notified and prevent spam.
#
# Examples:
#   - event_key='plex_down', prev_status='OK', new_status='FAIL'
#   - event_key='disk_/mnt/Array_warn', prev_status='OK', new_status='WARN'

CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_key TEXT NOT NULL,
    prev_status TEXT,
    new_status TEXT NOT NULL,
    message TEXT NOT NULL,
    notified BOOLEAN NOT NULL DEFAULT 0,
    notified_ts DATETIME,
    maintenance_suppressed BOOLEAN NOT NULL DEFAULT 0,
    sleep_suppressed BOOLEAN NOT NULL DEFAULT 0
);
"""

CREATE_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_key ON events(event_key);
CREATE INDEX IF NOT EXISTS idx_events_notified ON events(notified);
"""

# =============================================================================
# Sleep Events Table
# =============================================================================
# Stores events that occurred during sleep hours for morning summary digest.
# Events are queued here during sleep schedule and cleared after summary is sent.
#
# Examples:
#   - Event during sleep: category='service', name='jellyfin', new_status='FAIL'
#   - Recovery during sleep: prev_status='FAIL', new_status='OK'

CREATE_SLEEP_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS sleep_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_key TEXT NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    prev_status TEXT,
    new_status TEXT NOT NULL,
    message TEXT NOT NULL,
    details_json TEXT
);
"""

CREATE_SLEEP_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_sleep_events_ts ON sleep_events(ts);
CREATE INDEX IF NOT EXISTS idx_sleep_events_key ON sleep_events(event_key);
"""

# =============================================================================
# Schema Version Table
# =============================================================================
# Tracks database schema version for future migrations
# Simple table with a single row containing the current schema version.

CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# Initial schema version insert
INSERT_SCHEMA_VERSION = """
INSERT OR IGNORE INTO schema_version (version) VALUES (?);
"""

# =============================================================================
# Schema Migrations
# =============================================================================

async def migrate_to_v030(db):
    """
    Migrate database from v0.1.0 to v0.3.0.
    
    Adds maintenance_suppressed column to events table to track alerts
    that were suppressed due to maintenance windows.
    
    Args:
        db: aiosqlite database connection
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check if column already exists
        cursor = await db.execute("PRAGMA table_info(events)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "maintenance_suppressed" not in column_names:
            logger.info("Adding maintenance_suppressed column to events table")
            await db.execute("""
                ALTER TABLE events 
                ADD COLUMN maintenance_suppressed BOOLEAN NOT NULL DEFAULT 0
            """)
            await db.commit()
            logger.info("Successfully migrated to schema v0.3.0")
        else:
            logger.debug("Column maintenance_suppressed already exists, skipping migration")
            
    except Exception as e:
        logger.error(f"Failed to migrate to v0.3.0: {e}", exc_info=True)
        raise


async def migrate_to_v100(db):
    """
    Migrate database from v0.3.1 to v1.0.0.

    Removes the UNIQUE constraint on event_key in the events table so the
    table becomes append-only — every state change gets its own row.

    SQLite does not support DROP CONSTRAINT, so the migration uses the
    standard table-recreation pattern:
      1. Create events_new without the UNIQUE constraint
      2. Copy all existing rows
      3. Drop the old table
      4. Rename events_new → events
      5. Recreate indexes

    Args:
        db: aiosqlite database connection
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("Creating events_new table without UNIQUE constraint on event_key")
        await db.execute("""
            CREATE TABLE events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_key TEXT NOT NULL,
                prev_status TEXT,
                new_status TEXT NOT NULL,
                message TEXT NOT NULL,
                notified BOOLEAN NOT NULL DEFAULT 0,
                notified_ts DATETIME,
                maintenance_suppressed BOOLEAN NOT NULL DEFAULT 0,
                sleep_suppressed BOOLEAN NOT NULL DEFAULT 0
            )
        """)

        logger.info("Copying existing events rows to events_new")
        await db.execute("INSERT INTO events_new SELECT * FROM events")

        logger.info("Dropping old events table")
        await db.execute("DROP TABLE events")

        logger.info("Renaming events_new to events")
        await db.execute("ALTER TABLE events_new RENAME TO events")

        logger.info("Recreating events indexes")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_key ON events(event_key)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_notified ON events(notified)")

        await db.commit()
        logger.info("Successfully migrated to schema v1.0.0 (events table is now append-only)")

    except Exception as e:
        logger.error(f"Failed to migrate to v1.0.0: {e}", exc_info=True)
        raise


async def migrate_to_v031(db):
    """
    Migrate database from v0.3.0 to v0.3.1.
    
    Adds:
    1. sleep_suppressed column to events table for tracking sleep-suppressed alerts
    2. sleep_events table for queuing events during sleep hours
    
    Args:
        db: aiosqlite database connection
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check if sleep_suppressed column already exists
        cursor = await db.execute("PRAGMA table_info(events)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "sleep_suppressed" not in column_names:
            logger.info("Adding sleep_suppressed column to events table")
            await db.execute("""
                ALTER TABLE events 
                ADD COLUMN sleep_suppressed BOOLEAN NOT NULL DEFAULT 0
            """)
            await db.commit()
            logger.info("Added sleep_suppressed column to events table")
        else:
            logger.debug("Column sleep_suppressed already exists, skipping")
        
        # Create sleep_events table if it doesn't exist
        logger.info("Creating sleep_events table")
        await db.execute(CREATE_SLEEP_EVENTS_TABLE)
        await db.executescript(CREATE_SLEEP_EVENTS_INDEXES)
        await db.commit()
        logger.info("Successfully migrated to schema v0.3.1")
            
    except Exception as e:
        logger.error(f"Failed to migrate to v0.3.1: {e}", exc_info=True)
        raise

