"""
Database schema definitions for HomeSentry

This module contains SQL schema definitions for all database tables.
Tables are designed to store metrics, service status, and state-change events.

Schema Version: 0.1.0
"""

SCHEMA_VERSION = "0.1.0"

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
    event_key TEXT NOT NULL UNIQUE,
    prev_status TEXT,
    new_status TEXT NOT NULL,
    message TEXT NOT NULL,
    notified BOOLEAN NOT NULL DEFAULT 0,
    notified_ts DATETIME
);
"""

CREATE_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_key ON events(event_key);
CREATE INDEX IF NOT EXISTS idx_events_notified ON events(notified);
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
