# HomeSentry - Project Summary

**Version:** 0.2.0  
**Status:** Production Ready  
**Last Updated:** January 27, 2026  
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

### In Progress (v0.3.0)

- [x] Maintenance windows for scheduled downtime (alert suppression during planned events)
- [x] Sleep schedule with morning summary digest (complete silence during sleep hours)
- [x] Plugin architecture foundation (AppModule base class, module discovery)
- [x] Home Assistant monitoring module
- [x] qBittorrent monitoring module
- [ ] Plex monitoring module
- [ ] Pi-hole monitoring module
- [ ] Jellyfin monitoring module
- [ ] Dashboard UI updates for app modules
- [ ] Module development documentation

### Next Up (v0.5.0)



### Completed (v0.1.0-dev)



- [x] Project structure and documentation

- [x] Agent preferences for development workflow

- [x] README, CHANGELOG, PROJECT_SUMMARY

- [x] .gitignore and LICENSE

- [x] Development environment guidelines

- [x] FastAPI application skeleton

- [x] Docker Dockerfile + docker-compose.yml

- [x] .env.example configuration template

- [x] requirements.txt with dependencies

- [x] Project directory structure (app/, collectors/, storage/, alerts/)

- [x] SQLite database schema



### In Progress (v0.1.0 MVP)



- [x] System collector (CPU, RAM, disk)

- [x] Service collector (HTTP checks)

- [x] Background scheduler

- [x] Discord alerting module

- [x] Basic HTML dashboard (completed - responsive UI with status cards, metrics table, events list)

- [x] Docker Dockerfile + docker-compose.yml

- [x] .env.example configuration template

- [x] requirements.txt with dependencies



### Next Up (v0.2.0)



- [ ] RAID status monitoring (mdadm, ZFS, btrfs)

- [ ] Enhanced event tracking

- [ ] State-change detection logic (OK → WARN → FAIL)



### Future Enhancements



**v0.5.0 - Installation & Configuration**

- [ ] Interactive setup wizard (like Pi-hole)

- [ ] Auto-detection of installed services

- [ ] Dynamic collector registration

- [ ] Web-based configuration UI



**v1.0.0 - Production Ready**

- [ ] Historical data visualization (charts)

- [ ] Authentication/authorization

- [ ] Mobile-responsive UI

- [ ] Multi-server support

- [ ] API rate limiting

- [ ] Unit test coverage > 80%



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

