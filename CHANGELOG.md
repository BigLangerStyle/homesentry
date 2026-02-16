# Changelog

All notable changes to HomeSentry will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-02-10

### Added

**Sustained State Checking with Grace Period**
- **Grace period tracking**: New `app/alerts/grace_period.py` module implements sustained state checking to prevent alerts on transient flaps
- **Configurable threshold**: `STATE_CHANGE_GRACE_CHECKS=3` env variable controls how many consecutive bad checks are required before alerting
- **Intelligent suppression**: Brief service hiccups (e.g., OK→FAIL→OK within 1-2 checks) are completely ignored and don't create events
- **Immediate recovery alerts**: Recovery to OK status always alerts immediately (no grace period for good news)
- **In-memory tracking**: Pending state changes tracked in memory, only logged to database after grace period threshold is met
- **Comprehensive logging**: Grace period decisions logged at INFO level for troubleshooting

**Example behavior:**
- Service flaps (1-2 checks): No alert, no database event, completely silent
- Sustained failure (3+ consecutive checks): Alert proceeds normally after threshold
- Recovery during grace period: Pending state discarded, no alert sent
- Recovery after alerting: Immediate recovery notification sent

### Fixed

**Morning Summary Timestamp Display**
- **Activity Log timestamps**: Changed format from 24-hour (`05:01`) to 12-hour with AM/PM (`5:01 AM`) for clarity
- **Timezone conversion**: Fixed UTC-to-local timezone conversion — timestamps now display in server's local time instead of UTC
- **Example**: Router reboot at 5:01 AM CST now correctly displays as `5:01 AM` instead of `11:01 AM` (UTC)
- **No logic changes**: Only affects display formatting in Discord morning summary — event collection and storage remain unchanged

**Duplicate Morning Summary**
- **Added last-sent tracker**: Module-level `_last_summary_sent` variable in `scheduler.py` prevents duplicate morning summaries
- **5-minute window**: Skips summary if already sent within last 5 minutes
- **Fixes issue**: Eliminated duplicate summaries at 5:59 AM and 6:00 AM when scheduler runs on both sides of the wake time boundary

**Maintenance Window Filtering in Morning Summaries**
- **Sleep + maintenance conflict**: Events occurring during maintenance windows (e.g., 5:00-5:15 AM router reboot) are now properly excluded from morning summaries
- **Architectural fix**: Morning summary generation now calls `should_suppress_alert()` with event timestamps to check maintenance windows
- **Previous behavior**: During sleep hours, ALL events were queued regardless of maintenance windows — router reboots generated 12+ events in morning summary
- **New behavior**: Events during maintenance windows are filtered out and counted separately — "Quiet Night" summary when only maintenance events occurred
- **Visibility**: Summary shows count of excluded maintenance events (e.g., "• 12 maintenance events excluded")
- **Audit trail preserved**: Maintenance events still logged to database, just excluded from Discord summary display

### Documentation
- Updated `.env.example` with detailed explanation of `STATE_CHANGE_GRACE_CHECKS` including examples
- Added comprehensive docstrings to `grace_period.py` explaining the sustained state checking pattern
- Updated module docstring in `check_morning_summary()` to document duplicate prevention logic

## [0.5.0] - 2026-02-01

### Fixed
- **Sleep schedule configuration**: Sleep schedule was disabled in `.env` - changed `SLEEP_SCHEDULE_ENABLED=false` to `true` to activate the feature
- **Sleep schedule boundary condition**: Fixed end time comparison to use exclusive boundary (`<` instead of `<=`), ensuring alerts resume exactly at configured wake time rather than one minute after
  - Sleep period is now `[start_time, end_time)` (half-open interval) matching standard time range conventions
  - Morning summaries now send on schedule instead of being suppressed at their configured time
  - Alert resumption happens immediately at wake time (e.g., 6:00 AM) instead of being delayed to 6:01 AM
- **Wake time adjusted**: Changed `SLEEP_SCHEDULE_END` from 07:30 to 06:00 in `.env` to match user's intended midnight-6AM sleep schedule

### Documentation
- Updated `.env.example` sleep schedule section to clarify that END time is exclusive (alerts resume AT this time, not after)
- Changed default wake time examples from 07:30 to 06:00 for consistency with common sleep schedules
- Added inline comment explaining START is inclusive, END is exclusive

## [0.4.0] - 2026-02-01

### Fixed

**Version Strings**
- Updated dashboard footer version from v0.3.0 to v0.4.0
- Updated `PROJECT_SUMMARY.md` version field to 0.4.0
- Updated `README.md` roadmap to reflect shipped versions (v0.1.0–v0.3.0) and current v0.4.0 polish release

**Code Quality**
- Normalized `validate_config` return type from `Tuple[bool, str]` to `tuple[bool, str]` in `homeassistant.py`, `pihole.py`, and `qbittorrent.py` (use built-in generic syntax, Python 3.9+)
- Removed unused `Tuple` from `typing` imports in `pihole.py` and `qbittorrent.py`
- Moved `import time` from inside `HomeAssistantModule.collect()` method body to module-level imports in `homeassistant.py`
- Fixed `validate_config` return type from `Tuple[bool, str]` to `tuple[bool, str]` in `discord.py`
- Normalized `validate_config` return type in `jellyfin.py` and `plex.py`
- Removed unused `Tuple` import from `jellyfin.py` and `plex.py`
- Fixed version string in `scheduler.py` startup log from v0.2.0 to v0.3.0
- Corrected version string in `main.py` application metadata from v0.2.0 to v0.3.0

**Configuration**
- Stripped CRLF corruption from `.env.example` (lines had 5–6 stray `\r` characters)
- Removed duplicate `SMART_POLL_INTERVAL` entry from `.env.example` SMART section (canonical entry retained in Polling Intervals)
- Removed stale "future feature" comment on `SMART_POLL_INTERVAL` — SMART monitoring shipped in v0.2.0
- Removed ghost `TAUTULLI_URL` entry and `TAUTULLI_MAINTENANCE_WINDOW` comment from `.env.example` — no Tautulli module exists
- Fixed Pi-hole notes in `.env.example`: removed v5 fallback references, module targets Pi-hole v6 session-based auth only
- Added missing `RAID_POLL_INTERVAL` to Polling Intervals section of `.env.example` (default: 300, matching RAID collector)
- Updated `RAID_POLL_INTERVAL` default from 120 to 300 in RAID section to match collector's actual poll interval

**File Organization** *(flagged for manual action — not applied in this commit)*
- Stray `gitignore` file (no dot prefix) at repo root should be deleted — `.gitignore` already exists
- `test_database.py` at repo root should be moved to `tests/`

## [0.3.0] - 2026-01-31

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

- **Plugin architecture foundation** for app-specific monitoring
  - AppModule base class with minimal interface (detect, collect, validate_config)
  - Automatic module discovery from `app/collectors/modules/` directory
  - Container-to-module matching via configurable detect() method
  - Hard limit enforcement (10 metrics max, 3 API calls max, 15 config options max per module)
  - Error isolation ensures module failures don't crash the system
  - Simple dict-based configuration from environment variables
  - Configuration pattern: `{APP_NAME}_{SETTING_NAME}` (e.g., `HOMEASSISTANT_API_URL`)
  - Integration with existing `metrics_samples` table (category='app')
  - Scheduler integration for automatic module execution alongside other collectors
  - Alert processing for app-specific metrics with configurable thresholds
  - Manual trigger endpoints for testing and debugging
  - Module validation helpers and comprehensive error handling
  - Foundation enables Home Assistant, qBittorrent, Plex, Pi-hole, Jellyfin modules
  - Clear example module template included in base.py docstring
  - No manual registration required - drop Python file in modules/ directory
  - API endpoints: `/api/modules`, `/api/modules/{app_name}`, `/api/collect/modules`
  - Module metadata includes display names, container mappings, and configuration limits
  - Future-ready for install UI to enumerate available modules
  - Enables community module contributions with clear, simple plugin API

- **Home Assistant monitoring module** - First app-specific monitoring module proving plugin architecture
  - Tracks entity count (total smart home devices/sensors)
  - Tracks automation count (number of configured automations)
  - Monitors API response time for health checking
  - Configurable alert thresholds for entity/automation growth
  - Auto-activates when homeassistant or hass container detected
  - Configuration via `HOMEASSISTANT_API_URL` and `HOMEASSISTANT_API_TOKEN`
  - Bearer token authentication with long-lived access tokens
  - Graceful error handling for API failures (401, 403, 404, 500, timeouts)
  - Stays within 3 API call limit per collection (2 calls used)
  - Metrics stored in database with category='app'
  - Scheduler integration for automatic collection every 60 seconds
  - Manual testing endpoint: `/api/collect/modules/homeassistant`

- **qBittorrent monitoring module** - Torrent client monitoring with bandwidth and disk space tracking
  - Tracks active torrents (downloading, seeding, queued)
  - Monitor download and upload speeds (Mbps)
  - Session statistics (total downloaded/uploaded in GB)
  - Free disk space monitoring in download directory
  - Alert on high torrent count or low disk space
  - Web API authentication with username/password
  - Session cookie management for authenticated API calls
  - Auto-detection of qBittorrent containers (including VPN variants)
  - Configurable thresholds for torrent count and disk space
  - Configuration via `QBITTORRENT_API_URL`, `QBITTORRENT_USERNAME`, `QBITTORRENT_PASSWORD`
  - Graceful handling of authentication failures and timeouts
  - Stays within 3 API call limit per collection (2 calls used)
  - Metrics: active_torrents, download_speed_mbps, upload_speed_mbps, disk_free_gb, session_downloaded_gb, session_uploaded_gb
  - Manual testing endpoint: `/api/collect/modules/qbittorrent`

- **Pi-hole monitoring module** - DNS sinkhole monitoring for network-wide ad blocking
  - Track queries blocked today (count and percentage)
  - Monitor total DNS queries and forwarded queries
  - Active client count (devices using Pi-hole)
  - Blocklist size (total blocked domains)
  - Alert on low block percentage (Pi-hole not effective)
  - Supports Pi-hole v6+ with session-based authentication
  - Uses app password (not web UI password) for API access
  - Auto-detection of Pi-hole containers and bare-metal installations
  - Bare-metal module support - runs without Docker container
  - Configurable thresholds for block percentage
  - Works with both Docker and systemd Pi-hole installations
  - Configuration via `PIHOLE_API_URL`, `PIHOLE_API_PASSWORD`, `PIHOLE_BARE_METAL`
  - Graceful handling of API failures and timeouts
  - Session-based auth flow: login → extract sid/csrf → use for API calls
  - Metrics: queries_blocked_today, total_queries_today, percent_blocked, active_clients, blocklist_size, queries_forwarded
  - Manual testing endpoint: `/api/collect/modules/pihole`

- **Plex Media Server monitoring module** - Streaming activity and library tracking
  - Track active streaming sessions (who's watching)
  - Monitor transcoding sessions (hardware vs software)
  - Total bandwidth usage across all streams
  - Library statistics (movies, TV shows, total items)
  - Alert on high transcode count (CPU load)
  - X-Plex-Token authentication
  - Bare-metal module support (runs without Docker container)
  - XML response parsing (Plex API uses XML, not JSON)
  - Auto-detection of Plex containers and systemd installations
  - Direct Play vs Transcoding visibility
  - Configurable transcoding thresholds
  - Works with both Docker and bare-metal Plex installations
  - Configuration via `PLEX_API_URL`, `PLEX_API_TOKEN`, `PLEX_BARE_METAL`
  - Graceful handling of API failures and timeouts
  - Library count optimization with X-Plex-Container-Size parameter
  - Metrics: active_streams, transcode_count, bandwidth_mbps, library_items, movie_count, tv_show_count
  - Manual testing endpoint: `/api/collect/modules/plex`

- **Jellyfin monitoring module** - Secondary media server monitoring (completes v0.3.0 app modules!)
  - Track active streaming sessions
  - Monitor transcoding sessions (hardware vs software)
  - Active user count (unique viewers)
  - Library statistics (movies, series, episodes)
  - Alert on high transcode count (CPU load)
  - API key authentication (X-Emby-Token header)
  - JSON response parsing (simpler than Plex XML)
  - Auto-detection of Jellyfin Docker containers
  - Direct Play vs Transcoding visibility
  - Configurable transcoding thresholds
  - Configuration via `JELLYFIN_API_URL`, `JELLYFIN_API_KEY`
  - Graceful handling of API failures and timeouts
  - Completes media server monitoring suite (Plex + Jellyfin)
  - Metrics: active_streams, transcode_count, active_users, library_items, movie_count, series_count, episode_count
  - API endpoints: /Sessions (streams/users), /Items/Counts (library stats)
  - Manual testing endpoint: `/api/collect/modules/jellyfin`

- **Dashboard UI updates for app modules** - Two-layer visual hierarchy for the monitoring dashboard
  - Application Layer section at top with dynamic app cards for each enabled module
  - Each app card shows 3-4 key metrics with status-colored indicators (✓ OK, ⚠ Warning, ✗ Error)
  - Infrastructure Layer section below with System Resources, Service Health, Docker, SMART, RAID subsections
  - New `/api/metrics/latest` endpoint returns both app and infrastructure metrics in one response
  - App metrics grouped by module prefix and filtered to card_metrics display list per app
  - JavaScript-driven rendering replaces server-side Jinja2 for app cards (fetches every 60s)
  - Human-readable formatting: commas on numbers, auto-scaling bandwidth (Mbps/Gbps), percentages
  - Responsive grid: 3 columns (desktop) → 2 (tablet) → 1 (mobile) for app cards
  - Status bubbling: app card reflects worst metric status across all its metrics
  - Removed meta refresh tag — polling handled by setInterval in JavaScript
  - Infrastructure subsections use consistent status cards with colored left-border indicators
  - Recent Alerts section preserved at bottom (server-rendered via Jinja2)

- **Bare-metal module support** - Run app modules without Docker containers
  - Modules can run against bare-metal services (systemd, native installs)
  - Configure with `{APP_NAME}_BARE_METAL=true` environment variable
  - Essential for mixed environments (some apps in Docker, some bare-metal)
  - Enables monitoring of Plex, Pi-hole, and other non-containerized services
  - Module runner checks for bare-metal flag and skips container requirement
  - Metrics stored with 'baremetal' as container name
  - Error isolation maintained for bare-metal modules
  - Paves way for Plex module (also bare-metal on MediaServer)

- **Dark mode** - Dashboard theme toggle with system-preference detection
  - Toggle button (☀️/🌙) in header switches between light and dark themes
  - Preference persists across page reloads via localStorage
  - Defaults to system preference (prefers-color-scheme) on first visit
  - All colors driven by CSS custom properties — single override block

- **Module development documentation** - Comprehensive guide for creating new app modules (`MODULES.md`)
  - Architecture overview: auto-discovery, container matching, config parsing, bare-metal support
  - Full explanation of the three required class attributes and `collect()` method interface
  - Hard limits reference with rationale (10 metrics, 3 API calls, 15 config options)
  - Configuration convention: environment variable prefix parsing with automatic type conversion
  - Threshold alerting convention (`{METRIC}_WARN` / `{METRIC}_FAIL` naming pattern)
  - Step-by-step walkthrough using a fictional Sonarr module (file creation through dashboard verification)
  - Reference table of all 5 existing modules: auth method, API calls, metrics, and mode
  - Dashboard card registration instructions (`APP_PREFIXES`, `APP_DISPLAY_NAMES`, `APP_CARD_METRICS` in `main.py`)
  - Designed to be self-contained — a developer reads it and can write a working module without reading source code

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

- **v0.4.0** (Released 2026-02-01) - Polish release: 22 fixes across code quality, configuration, and documentation
- **v0.3.0** (Released 2026-01-31) - Plugin architecture and app-specific modules
- **v0.2.0** (Released 2026-01-27) - Infrastructure monitoring (Docker, SMART, RAID)
- **v0.1.0** (Released 2026-01-25) - MVP with system monitoring, service checks, Discord alerts
- **v0.5.0** (Future) - Interactive installer, configuration UI
- **v1.0.0** (Future) - Historical charts, authentication, production polish
