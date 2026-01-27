# Changelog

All notable changes to HomeSentry will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v0.3.0
- Plugin architecture for app-specific monitoring modules
- Curated modules for Home Assistant, qBittorrent, Plex, Pi-hole, Jellyfin
- Enhanced dashboard UI with app module displays
- Module documentation and development guide

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
  - Rebuild progress monitoring with speed and ETA
  - Automatic array discovery or manual configuration
  - CRITICAL alerts for array degradation (highest priority)
  - Warning alerts for rebuild progress with periodic updates
  - Success alerts when array is restored to healthy state
  - Manual collection endpoint (`/api/collect/raid`)
  - Integrated with background scheduler (every 2 minutes - more urgent than SMART)
  - File-based parsing (no root privileges required)
  - Configurable array list and poll interval via environment variables

### Technical Improvements
- Enhanced scheduler with multi-frequency collection cycles (Docker: 60s, RAID: 2min, SMART: 10min)
- Async subprocess execution for system monitoring tools
- Robust regex-based parsing for SMART and RAID data
- File-based monitoring (no root privileges required for RAID)
- Comprehensive error handling and graceful degradation

### Deployment Changes
- Docker socket mounted for container monitoring (`/var/run/docker.sock:ro`)
- Device mounts for SMART monitoring (`/dev/sda`, `/dev/sdb`, `/dev/sdc`, `/dev/sdd`)
- CAP_SYS_RAWIO capability for raw device access
- smartmontools installed in Docker container

### Configuration
- 10 new environment variables for Docker, SMART, and RAID configuration
- Poll interval configuration per collector type
- Threshold configuration for temperature and resource usage
- Device and array list configuration

### Completed in v0.2.0
- ✅ Docker container monitoring (status, health, restarts, resources)
- ✅ SMART drive health monitoring (health status, temperature, sectors, alerts)
- ✅ RAID array monitoring (array health, disk tracking, rebuild progress, alerts)
- ✅ Enhanced scheduler with multi-frequency collection
- ✅ Critical infrastructure alerting system


---

## [0.1.0] - 2026-01-25

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
  - `insert_metric_sample()` - Insert metric data
  - `insert_service_status()` - Insert service health check
  - `insert_event()` - Insert state-change event
  - `get_latest_metrics()` - Query recent metrics
  - `get_latest_events()` - Query recent events
  - `get_latest_service_status()` - Query recent service checks
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
  - Helper functions for event state tracking (`get_latest_event_by_key`, `update_event_notified`)
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
  - JSON API endpoints for programmatic access:
    - `/api/dashboard/status` - Current status as JSON
    - `/api/dashboard/events` - Recent events as JSON
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

- **v0.3.0** (Planned) - Plugin architecture, app-specific modules (HA, qBittorrent, Plex, Pi-hole, Jellyfin)
- **v0.2.0** (Released 2026-01-27) - Docker monitoring, SMART health checks, RAID array monitoring
- **v0.1.0** (Released 2026-01-25) - MVP with system monitoring, service checks, Discord alerts, web dashboard
- **v0.5.0** (Future) - Interactive installer, configuration UI
- **v1.0.0** (Future) - Historical charts, authentication, UI polish
