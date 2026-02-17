# HomeSentry - Project Summary

**Version:** 0.7.0  
**Status:** Production Ready  
**Last Updated:** February 16, 2026  
**Target Platform:** Linux (Ubuntu/Debian) + Docker  
**Primary Language:** Python 3.11+  

---



## Project Overview



HomeSentry is a self-hosted health monitoring dashboard for home servers. It's designed as both a **learning project** (to master Python, FastAPI, Docker, and system monitoring) and a **genuinely useful tool** for managing home lab infrastructure.



### Core Philosophy



1. **Ship Fast, Iterate** - v0 focused on basic functionality, improvements come later

2. **Modular Design** - Collectors are independent and can be added/removed easily

3. **Resilience First** - Collector failures don't crash the app

4. **User-Friendly** - Simple setup, clear dashboard, actionable alerts

5. **Learn by Building** - Code is readable and well-commented for educational value



---



## Architecture



### High-Level Design



```

┌─────────────────────────────────────┐

│      FastAPI Application            │

│  (Web Server + API + Dashboard)     │

└──────────────┬──────────────────────┘

               │

      ┌────────┴────────┐

      │   Scheduler     │  (Background Tasks)

      └────────┬────────┘

               │

    ┌──────────┼──────────┐

    │          │          │

┌───▼───┐  ┌──▼──┐  ┌───▼────┐

│System │  │SMART│  │Services│  (Collectors)

└───┬───┘  └──┬──┘  └───┬────┘

    │         │         │

    └─────────┼─────────┘

              │

       ┌──────▼──────┐

       │   SQLite    │  (Storage)

       └──────┬──────┘

              │

       ┌──────▼──────┐

       │   Discord   │  (Alerts)

       └─────────────┘

```



### Technology Stack



- **Backend:** Python 3.11+ with FastAPI

- **Database:** SQLite (simple, no external dependencies)

- **Frontend:** HTML + CSS (maybe JS later for charts)

- **Deployment:** Docker + Docker Compose

- **Alerts:** Discord webhooks (expandable to email, Slack, etc.)

- **Monitoring Libraries:** psutil, requests, docker-py, smartmontools



---



## Current Status

### Completed (v0.1.0)

- [x] Project structure and documentation
- [x] FastAPI application skeleton
- [x] SQLite database schema
- [x] System collector (CPU, RAM, disk)
- [x] Service collector (HTTP checks)
- [x] Background scheduler
- [x] Discord alerting module
- [x] Web dashboard UI
- [x] Docker Dockerfile + docker-compose.yml

### Completed (v0.2.0) - Infrastructure Monitoring Release

- [x] Docker container monitoring (status, health, restarts, resources)
- [x] SMART drive health checks (health status, temperature, reallocated sectors, alerts)
- [x] RAID status monitoring (array health, disk tracking, rebuild progress, alerts)
- [x] Enhanced scheduler with multi-frequency collection
- [x] Critical infrastructure alerting

### Completed (v0.3.0) - Plugin Architecture & App Modules

- [x] Maintenance windows for scheduled downtime (alert suppression during planned events)
- [x] Sleep schedule with morning summary digest (complete silence during sleep hours)
- [x] Plugin architecture foundation (AppModule base class, module discovery)
- [x] Home Assistant monitoring module
- [x] qBittorrent monitoring module
- [x] Pi-hole monitoring module
- [x] Plex monitoring module
- [x] Jellyfin monitoring module
- [x] Dashboard UI updates for app modules
- [x] Dark mode for dashboard
- [x] Module development documentation

### Completed (v0.4.0) - Polish Release

- [x] Normalized `validate_config` return types to `tuple[bool, str]` (homeassistant, pihole, qbittorrent, jellyfin, plex, discord)
- [x] Removed unused `Tuple` imports from typing in all affected modules
- [x] Moved `import time` to module level in homeassistant.py
- [x] Fixed version strings in main.py and scheduler.py (were stuck at v0.2.0)
- [x] Stripped CRLF corruption from .env.example
- [x] Removed duplicate SMART_POLL_INTERVAL from .env.example
- [x] Removed stale "future feature" comment on SMART (shipped v0.2.0)
- [x] Removed ghost Tautulli references from .env.example
- [x] Fixed Pi-hole notes: removed v5 fallback references, module is v6-only
- [x] Added RAID_POLL_INTERVAL to Polling Intervals section (default: 300)
- [x] Updated RAID_POLL_INTERVAL default to 300 to match collector
- [x] Updated dashboard footer to v0.4.0
- [x] Updated README roadmap to reflect all shipped versions
- [x] Updated CHANGELOG with complete v0.4.0 section

### Completed (v0.5.0) - Installation & Configuration

- [x] Interactive TUI setup installer (scripts/setup.sh)
- [x] Automatic service detection (Docker, systemd, HTTP)
- [x] Menu-driven module selection with pre-checked detected services
- [x] Guided configuration screens for each module
- [x] Discord webhook validation with test message
- [x] Bare-metal service support (Plex, Pi-hole)
- [x] Configuration preview and .env generation
- [x] Eliminates manual .env editing for first-time setup
- [x] Web-based configuration UI (/config)
- [x] Browser-based settings management with organized sections
- [x] Per-module enable/disable toggles
- [x] Sensitive field masking with bullet characters (••••••••••••••••)
- [x] Atomic .env file writes
- [x] Configuration API endpoints (GET/POST /api/config)
- [x] Full light mode support for config UI
- [x] Module status badges (green "ENABLED" / gray "DISABLED")
- [x] Number input spinners visible
- [x] Custom dropdown styling for both themes
- [x] Config reads from environment variables (proper Docker pattern)
- [x] Immediate effect (updates both .env and process environment)
- [x] Prominent config button in dashboard header
- [x] Console logging for debugging
- [x] Replaced hardcoded app card registration in `main.py` with dynamic registration from discovered modules
- [x] Added `CARD_METRICS` class attribute to `AppModule` base class
- [x] Each module now self-declares its dashboard card metrics
- [x] Dashboard card data built dynamically via `get_discovered_modules()` at query time
- [x] New modules no longer require manual edits to `main.py`

### Completed (v0.6.0) - Sustained State Checking

- [x] Grace period tracking module (`app/alerts/grace_period.py`)
- [x] Configurable grace period via `STATE_CHANGE_GRACE_CHECKS` environment variable
- [x] In-memory tracking of pending state changes
- [x] Brief flaps (1-2 checks) completely ignored - no alerts, no database events
- [x] Sustained failures (3+ consecutive checks) alert normally after threshold
- [x] Immediate recovery alerts (no grace period for good news)
- [x] Integration with existing alert processing in `rules.py`
- [x] Fixed duplicate morning summary issue in `scheduler.py`
- [x] Added last-sent tracker to prevent duplicate summaries within 5-minute window
- [x] Comprehensive logging of grace period decisions

### Completed (v0.7.0) - Historical Data Charts

- [x] New `get_metric_history()` function in `app/storage/db.py` with SQLite time bucketing
- [x] New `get_available_chart_metrics()` function — dynamically discovers chartable metrics with data
- [x] `GET /api/metrics/history/available` endpoint — returns chartable metrics list with labels + units
- [x] `GET /api/metrics/history?metric=&hours=` endpoint — returns bucketed time-series JSON for Chart.js
- [x] "Historical Trends" section in dashboard.html below Infrastructure Layer
- [x] 2-column chart grid with Chart.js 4.4.1 (CDN, no Python dependency changes)
- [x] Default charts: CPU %, RAM %, disk-free-GB (all mounts with data)
- [x] Time range selector: 6h / 24h / 7d — refreshes all charts on click
- [x] Dark mode chart colors — grid lines, ticks, legend update on theme toggle
- [x] Chart container CSS in styles.css with dark mode CSS variable support

### Future Enhancements

**v0.8.0 - Polish Release** *(in progress — intentionally long-running)*

- [x] Docs catch-up — CHANGELOG Version History Summary, PROJECT_SUMMARY Future Enhancements, README roadmap, MODULES.md all need updating
- [ ] Data retention — `metrics_samples` grows forever; add nightly cleanup job with `METRICS_RETENTION_DAYS` env var (default 30)
- [ ] Dashboard UX — footer version string; add "Last refreshed" indicator; verify chart empty-state handling
- [ ] Additional polish items to be added as they surface during normal use

**v0.9.0 - Security & Reliability**

- [ ] Authentication/authorization
- [ ] API rate limiting
- [ ] Unit test coverage > 80%

**v1.0.0 - Production Ready**

- [ ] Multi-server support
- [ ] Mobile-responsive UI
- [ ] Production hardening and final polish



---



## Development Workflow



### On Windows (Development Machine)



1. Edit code in Cursor/VSCode

2. Run linters (Black, pylint)

3. Test locally if possible

4. Commit to Git

5. Push to GitHub



### On Linux Server (MediaServer)



1. SSH into MediaServer

2. `cd /path/to/homesentry`

3. `git pull`

4. `docker compose up --build -d`

5. View logs: `docker compose logs -f`



This separation allows development on Windows while deploying to Linux.



---



## Key Design Decisions



### Why SQLite?

- **Simplicity** - No external database server required

- **Portability** - Single file, easy to backup

- **Performance** - More than sufficient for single-server metrics

- **No Overhead** - Embedded, no network latency



### Why Docker?

- **Isolation** - Doesn't conflict with system packages

- **Reproducibility** - Same environment everywhere

- **Easy Updates** - Rebuild and restart

- **Host Access** - Can still access /proc, /sys via bind mounts



### Why FastAPI?

- **Modern** - Async support, type hints, automatic docs

- **Fast** - Built on Starlette and Pydantic

- **Easy** - Simple to learn, great for education

- **Documented** - Auto-generated API docs via OpenAPI



### Why Discord Webhooks?

- **Simple** - Just HTTP POST to a URL

- **Free** - No API limits for webhooks

- **Popular** - Many home lab users already use Discord

- **Expandable** - Easy to add other channels later



---



## Monitoring Strategy



### What We Monitor



**System Resources:**

- CPU usage (%)

- RAM usage (% and absolute)

- Disk usage (% and free GB)

- Load average (optional)

- Uptime



**Storage Health (SMART):**

- Reallocated sectors

- Pending sectors

- Offline uncorrectable sectors

- Drive temperature

- Overall health status (PASSED/FAILED)



**RAID Status:**

- Array health (clean/degraded/rebuilding)

- Disk member status

- Rebuild progress



**Services:**

- HTTP response code (200 = OK)

- Response time

- Service reachability



**Docker Containers:**

- Container status (running/stopped)

- Health check status (if defined)

- Restart count

- Resource usage



### Alert Strategy



**State-Change Based:**

- Only alert when status changes (OK → WARN → FAIL)

- Cooldown period (30 min) to prevent spam

- Recovery notifications (FAIL → OK)



**Priority Levels:**

- **OK** - Everything is fine

- **WARN** - Approaching thresholds (e.g., disk < 20%)

- **FAIL** - Critical issue (e.g., service down, disk failed)



**Example Thresholds:**

- Disk free < 15% or < 50GB → WARN

- Disk free < 5% or < 10GB → FAIL

- Service down > 2 minutes → FAIL

- Container restart count delta > 5/hour → WARN

- SMART pending sectors > 0 → WARN

- RAID degraded → FAIL



---



## Database Schema



### Tables



**metrics_samples:**

- `id` (pk)

- `ts` (datetime)

- `category` (system|disk|smart|docker|service|raid)

- `name` (e.g., "cpu_percent", "disk_/mnt/Array_free_gb")

- `value_num` (float, nullable)

- `value_text` (text, nullable)

- `status` (OK|WARN|FAIL)

- `details_json` (text)



**service_status:**

- `id` (pk)

- `ts` (datetime)

- `service` (plex|jellyfin|docker|pihole|etc)

- `status` (OK|WARN|FAIL)

- `response_ms` (float, nullable)

- `details_json` (text)



**events:**

- `id` (pk)

- `ts` (datetime)

- `key` (unique incident key, e.g., "plex_down")

- `prev_status` (OK|WARN|FAIL)

- `new_status` (OK|WARN|FAIL)

- `message` (text)

- `notified` (bool)

- `notified_ts` (datetime, nullable)



---



## API Endpoints



### Dashboard & Status



- `GET /` - HTML dashboard (visual monitoring interface)

- `GET /api/dashboard/status` - JSON status summary (current system and service status)

- `GET /api/dashboard/events?limit=20` - Recent state changes/alerts as JSON

- `GET /healthz` - Liveness check for Docker health

- `GET /api/collect/system` - Manual trigger for system metrics collection (testing)

- `GET /api/collect/services` - Manual trigger for service health checks (testing)

- `GET /api/test-alert` - Send test Discord alert (webhook validation)



### Future Endpoints (v1.0+)



- `GET /api/metrics?hours=24` - Historical time-series metrics

- `GET /api/config` - Get configuration

- `POST /api/config` - Update configuration

- `POST /api/collectors/enable/{name}` - Enable collector

- `POST /api/collectors/disable/{name}` - Disable collector



---



## Configuration



### Environment Variables



All configuration via `.env` file:



```ini

# Required

DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...



# Polling Intervals

POLL_INTERVAL=60              # System/service checks (seconds)

SMART_POLL_INTERVAL=600       # SMART checks (seconds)



# Service URLs

PLEX_URL=http://localhost:32400

JELLYFIN_URL=http://localhost:8096

PIHOLE_URL=http://localhost:80



# Thresholds

DISK_FREE_PERCENT_WARN=15

DISK_FREE_GB_WARN=50

CONTAINER_RESTART_THRESHOLD=5

SERVICE_DOWN_WINDOW=120       # Seconds before alerting

```



---



## Testing Strategy



### Phase 1 (v0.1.0) - Manual Testing

- Run locally and verify collectors work

- Deploy to MediaServer and monitor for 24 hours

- Trigger test alerts



### Phase 2 (v0.2.0+) - Unit Tests

- Test collector result parsing

- Test alert state-change logic

- Test database operations

- Test rollup/aggregation functions



### Phase 3 (v1.0.0) - Integration Tests

- End-to-end API testing

- Load testing (can handle 1000+ samples)

- Failure simulation



---



## Known Limitations



### Current:

- Single-server only (can't monitor multiple servers)

- No authentication (dashboard is publicly accessible if exposed)

- No historical charts (data is stored but not visualized)

- Basic HTML UI (no real-time updates, requires refresh)

- English only



### Future Improvements:

- Multi-server support (v1.0+)

- Authentication/authorization (v1.0+)

- Historical data visualization (v1.0+)

- Real-time WebSocket updates (v1.5+)

- Mobile app (v2.0+)



---



## Security Considerations



### Current:

- No authentication (safe on LAN only)

- Discord webhook URL in plaintext (in .env)

- SQLite database is world-readable (file permissions)



### Recommended:

- Deploy behind reverse proxy with auth (Nginx + basic auth)

- Don't expose port 8000 to internet

- Set proper file permissions on .env (600)

- Use Cloudflare Tunnel or VPN for remote access



### Future:

- Built-in authentication (v1.0)

- API keys for programmatic access

- Encrypted credential storage



---



## Learning Objectives



This project teaches:



1. **Python Fundamentals**

   - Type hints

   - Async/await

   - Error handling

   - Logging



2. **Web Development**

   - FastAPI framework

   - REST API design

   - HTML templating

   - JSON serialization



3. **System Administration**

   - Linux system metrics (/proc, /sys)

   - SMART disk monitoring

   - RAID management

   - Docker operations



4. **Database Design**

   - Schema design

   - SQLite operations

   - Time-series data



5. **DevOps**

   - Docker containers

   - Docker Compose

   - Environment variables

   - Deployment workflows



6. **Monitoring Concepts**

   - Metrics vs logs vs traces

   - Thresholds and alerting

   - State-change detection

   - Collector patterns



---



## Inspiration & References



- **Pi-hole** - Installation UX and simplicity

- **Netdata** - Real-time monitoring approach

- **Grafana** - Dashboard design patterns

- **Prometheus** - Time-series storage concepts

- **Home Assistant** - Auto-discovery of services



---



## Contributing



This is primarily a personal learning project, but contributions are welcome!



**Areas where help would be appreciated:**

- Testing on different Linux distributions

- UI/CSS improvements

- Additional collector modules

- Documentation improvements

- Bug reports



---



## License



MIT License - Free to use, modify, and distribute.



---



## Author



Built as a learning project and portfolio piece for real-world use on a home media server (MediaServer).



**Goals:**

- Learn Python by building something actually useful

- Have a second side project for resume (alongside Prompt Pins)

- Solve real problems with my home server

- Share knowledge with others running home labs



---



## Contact & Support



- **GitHub Issues** - For bugs and feature requests

- **GitHub Discussions** - For questions and ideas

- **README.md** - For installation and usage

- **CHANGELOG.md** - For version history



---



**Remember**: HomeSentry is designed to be your server's watchdog—set it up once, then relax knowing it's keeping an eye on things. 🐕‍🦺

