# Changelog

All notable changes to HomeSentry will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0-dev] - 2026-01-27

### Summary
Application-layer monitoring release introducing plugin architecture for app-specific monitoring modules. This release transforms HomeSentry into a Docker-native monitoring platform with deep integrations for popular home lab applications.

### Planned for v0.3.0
- **Plugin architecture foundation** - Modular system for app-specific monitoring
- **Curated app modules** - Home Assistant, qBittorrent, Plex, Pi-hole, Jellyfin
- **Enhanced dashboard UI** - App-specific metrics display with visual hierarchy
- **Module documentation** - Plugin development guide and API reference

### Added
- **Maintenance windows** for scheduled downtime alert suppression
  - Per-service maintenance schedules via environment variables
  - Global maintenance window for router reboots or system-wide maintenance
  - Time-based alert suppression (alerts logged but not sent to Discord)
  - Day-of-week filtering for weekly maintenance schedules
  - Database tracking of maintenance-suppressed alerts via new `maintenance_suppressed` column
  - Recovery alerts sent after maintenance window ends
  - Critical infrastructure alerts (SMART, RAID) exempt from suppression
  - Support for midnight-spanning maintenance windows (e.g., 23:45-00:15)
  - Configurable via .env with HH:MM-HH:MM format
  - Service names are case-insensitive for flexible configuration
  - Detailed logging of suppression reasons for debugging
  - Schema migration from v0.1.0 to v0.3.0 for existing databases

- **Sleep schedule with morning summary digest**
  - Configurable sleep hours for complete alert suppression
  - Suppress all alerts (down, recovery, warnings) during sleep hours
  - Optional morning summary digest at configurable wake time
  - Summary shows overnight activity, service restarts, and ongoing issues
  - "Quiet night" message when no events occurred during sleep
  - Optional critical infrastructure exemption (SMART, RAID) via `SLEEP_ALLOW_CRITICAL_ALERTS`
  - Sleep schedule takes precedence over maintenance windows
  - Midnight-spanning schedules supported (e.g., 23:00-07:00)
  - Events queued in dedicated `sleep_events` table during sleep hours
  - Database tracking via new `sleep_suppressed` column in events table
  - Configurable via .env with HH:MM format for start/end times
  - Automatic morning digest delivery via scheduler at wake time
  - Schema migration from v0.3.0 to v0.3.1 for sleep schedule support

---

## [0.2.0] - 2026-01-27

### Summary
Major infrastructure monitoring release focused on Docker-native observability and critical server health tracking. This release adds comprehensive container monitoring, drive health tracking, and RAID array monitoring - providing complete visibility into home lab infrastructure health.

### Added
- **Docker container monitoring** via Docker API
  - Container status tracking (running, stopped, paused, etc.)
  - Health check status monitoring (healthy, unhealthy, starting, none)
  - Restart count tracking to detect crash-looping containers
  - CPU and memory usage per container
  - Automatic state-change detection and alerting
  - Manual collection endpoint (`/api/collect/docker`)
  - Integrated with background scheduler for autonomous monitoring
  - Read-only Docker socket mount for secure access
- **SMART drive health monitoring** via smartctl from smartmontools
  - Overall SMART health status tracking (PASSED/FAILED)
  - Drive temperature monitoring with configurable thresholds
  - Reallocated sectors detection (early warning of drive failure)
  - Pending sectors monitoring (sectors waiting to be reallocated)
  - Uncorrectable sectors tracking
  - Power-on hours tracking for drive age analysis
  - Multi-drive concurrent collection for performance
  - Automatic state-change detection and alerting for all critical metrics
  - Manual collection endpoint (`/api/collect/smart`)
  - Integrated with background scheduler (less frequent - every 10 minutes)
  - CAP_SYS_RAWIO capability in Docker for raw device access
  - Configurable drive list and temperature thresholds via environment variables
  - smartmontools installed in Docker container
- **RAID array monitoring** via /proc/mdstat (mdadm software RAID)
  - Array health status tracking (clean, degraded, rebuilding, failed)
  - Individual disk status monitoring within arrays (active, failed, spare)
  - Active vs expected disk count tracking
  - Rebuild progress monitoring with percentage and ETA
  - Multi-array support for systems with multiple RAID volumes
  - Automatic state-change detection and alerting for critical status changes
  - Manual collection endpoint (`/api/collect/raid`)
  - Integrated with background scheduler
  - Read-only mount of /proc for array status access
- **Enhanced scheduler** with multi-frequency collection
  - Different poll intervals for different collector types
  - System/Docker: Every 60 seconds (configurable via POLL_INTERVAL)
  - SMART: Every 10 minutes (configurable via SMART_POLL_INTERVAL)
  - Services/RAID: Every 60 seconds (same as system)
  - Intelligent next-run calculation based on collector-specific intervals
- **Critical infrastructure alerting**
  - State-change alerts for Docker containers (healthy → unhealthy, running → stopped)
  - SMART health alerts for drive failures and temperature warnings
  - RAID degradation and rebuild alerts
  - Sector count increase alerts (reallocated, pending, uncorrectable)
  - Integrated with existing Discord webhook system

### Completed in v0.2.0
- ✅ Docker container monitoring (status, health, restarts, resources)
- ✅ SMART drive health monitoring (health status, temperature, sectors, alerts)
- ✅ RAID array monitoring (array health, disk tracking, rebuild progress, alerts)
- ✅ Enhanced scheduler with multi-frequency collection
- ✅ Critical infrastructure alerting system

---

## [0.1.0] - 2026-01-25

### Summary
Initial release establishing the foundation for HomeSentry with system monitoring, service health checks, Discord alerting, and web dashboard.

### Added
- Initial project structure and documentation
- Agent preferences for development workflow
- Comprehensive README with architecture overview
- MIT License
- Python .gitignore template
- **FastAPI application skeleton** with health check endpoint (`/healthz`)
- **Root endpoint** (`/`) with welcome message and status
- **Docker deployment configuration** (Dockerfile + docker-compose.yml)
- **Environment-based configuration** (.env.example template)
- **Python dependency management** (requirements.txt with pinned versions)
- **Project directory structure** for modular development (collectors, storage, alerts)
- **Logging configuration** with configurable log levels
- **CORS middleware** for future frontend development
- **SQLite database schema** with three core tables (metrics_samples, service_status, events)
  - Metrics samples table for time-series data from all collectors
  - Service status table for HTTP health check results
  - Events table for state-change tracking and alerting
  - Schema version table for future database migrations
- **Database initialization** on application startup
- **Async database operations** using aiosqlite
- **Helper functions** for inserting and querying metrics, service status, and events
- **System metrics collector** for monitoring server resources
  - CPU usage percentage (per-core and average)
  - Memory usage (total, available, used, percentage)
  - Disk space tracking (total, used, free, percentage)
  - Automatic insertion into metrics_samples table
  - Configurable monitoring paths via environment variables
  - Status determination (OK/WARN/FAIL) based on thresholds
  - Manual collection endpoint `/api/collect/system` for testing
- **Service health check collector** for monitoring HTTP services
  - HTTP GET requests with timeout handling
  - Response time measurement in milliseconds
  - Status code tracking (2xx, 3xx, 4xx, 5xx)
  - Configurable services via environment variables
  - Support for Plex, Jellyfin, Pi-hole, Home Assistant, qBittorrent, Tautulli
  - Graceful error handling for connection failures and timeouts
  - Concurrent service checks for performance
  - Automatic insertion into service_status table
  - Status determination (OK/WARN/FAIL) based on response
  - Manual collection endpoint `/api/collect/services` for testing
  - Configurable timeout (SERVICE_CHECK_TIMEOUT) and slow threshold (SERVICE_SLOW_THRESHOLD)
- **Discord webhook alerting system** with intelligent state-change detection
  - Rich Discord embeds with color-coding and formatted messages
  - State-change detection (OK → WARN → FAIL transitions)
  - Alert cooldown periods to prevent notification spam (default: 30 minutes)
  - Recovery notifications (automatic alerts when issues resolve)
  - Event tracking and deduplication via events table
  - Category-specific alert formatting (services, system metrics, disk space)
  - Test alert endpoint (`/api/test-alert`) for webhook validation
  - Configurable webhook URL and cooldown via environment variables
  - Async webhook delivery to prevent blocking
  - Comprehensive logging for debugging alert delivery
  - Helper functions for event state tracking
- **Background scheduler** for autonomous monitoring
  - Automatic collection of system metrics and service health checks
  - Configurable polling interval (default: 60 seconds)
  - Runs collectors concurrently for performance
  - Automatic alert processing after each collection
  - Graceful startup and shutdown with FastAPI lifecycle
  - Error recovery - continues running even if collectors fail
  - Intelligent sleep timing (accounts for collection duration)
  - Initial collection runs immediately on startup
  - Collection cycle logging with duration tracking
  - Warning when collections approach poll interval duration
- **Web dashboard UI** for visual monitoring and real-time status
  - Clean, responsive HTML interface using Jinja2 templates
  - Real-time status overview with color-coded indicators (green/yellow/red)
  - System metrics display (CPU, RAM, disk usage with percentages)
  - Service health status display (Plex, Jellyfin, etc. with response times)
  - Recent metrics table showing last 10 data points
  - Recent events/alerts list showing last 20 state changes
  - Mobile-friendly responsive layout (works on phones, tablets, desktop)
  - Auto-refresh every 60 seconds (meta refresh tag)
  - Professional CSS styling with modern color scheme
  - No-data states handled gracefully
  - Static file serving for CSS assets
  - Dashboard route (`/`) renders HTML instead of JSON
  - JSON API endpoints for programmatic access
  - Footer with version info and quick links to API docs

### Completed in v0.1.0
- ✅ FastAPI web server with HTML dashboard
- ✅ System collector (CPU, RAM, disk usage)
- ✅ Service HTTP health checks (Plex, Jellyfin, etc.)
- ✅ SQLite database schema
- ✅ Discord webhook alerting
- ✅ Background scheduler for autonomous monitoring
- ✅ Docker deployment configuration
- ✅ Web dashboard UI with responsive design

---

## Version History Summary

- **v0.3.0-dev** (Current) - Plugin architecture and app-specific modules
- **v0.2.0** (Released 2026-01-27) - Infrastructure monitoring (Docker, SMART, RAID)
- **v0.1.0** (Released 2026-01-25) - MVP with system monitoring, service checks, Discord alerts
- **v0.5.0** (Future) - Interactive installer, configuration UI
- **v1.0.0** (Future) - Historical charts, authentication, production polish
