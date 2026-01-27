# Changelog

All notable changes to HomeSentry will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0-dev] - 2026-01-26

### Planned for v0.2.0
- Docker container monitoring (status, health checks, restart counts)
- SMART drive health checks (via smartctl)
- RAID status monitoring (mdadm arrays)
- Enhanced event tracking and state management

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

- **v0.2.0-dev** (Current) - Docker monitoring, SMART checks, RAID status
- **v0.1.0** (Released 2026-01-25) - MVP with system monitoring, service checks, Discord alerts, web dashboard
- **v0.5.0** (Planned) - Interactive installer + modular collectors
- **v1.0.0** (Future) - Historical charts + authentication + UI polish
