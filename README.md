# HomeSentry

**Your Server's Personal Watchdog** 🐕‍🦺

A Python-based health monitoring dashboard for home servers that watches your infrastructure 24/7 and alerts you the moment something goes wrong.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What is HomeSentry?

HomeSentry is a self-hosted monitoring solution designed specifically for home lab environments. It continuously monitors your server's health and sends Discord notifications when issues are detected—before they become disasters.

Think of it as your server's guardian angel: quiet when everything's fine, loud when it's not.

### Key Features

✅ **Available Now (v0.8.0):**
- **System Monitoring** - Real-time CPU, RAM, and disk usage tracking
- **Service Checks** - HTTP health checks for Plex, Jellyfin, Pi-hole, and other web services
- **Docker Monitoring** - Container health, restart counts, and resource usage
- **SMART Health** - Hard drive health monitoring with predictive failure detection
- **RAID Status** - Track RAID array health, disk status, and rebuild progress
- **Smart Alerts** - Discord webhooks with sustained state checking (no spam from transient flaps!)
- **Web Dashboard** - Clean, responsive UI showing current status at a glance
- **Configuration UI** - Web-based settings management with module toggles
- **Historical Charts** - Time-series visualization with Chart.js, 6h/24h/7d range selector
- **Autonomous Operation** - Background scheduler runs 24/7, alerts automatically
- **Historical Data** - SQLite database tracks all metrics over time

🔮 **Coming Soon:**
- **Data Retention** - Configurable automatic cleanup of old metrics (v0.8.0)
- **Authentication** - Login and access control (v0.9.0)

---

## Why HomeSentry?

Home servers are amazing, but they require babysitting. Hard drives fail, services crash, storage fills up—and without monitoring, you won't know until it's too late.

**HomeSentry solves this by:**
- ✅ Watching everything automatically
- ✅ Alerting you only when state changes (OK → WARNING → CRITICAL)
- ✅ Running in Docker (no system package conflicts)
- ✅ Using minimal resources
- ✅ Being simple to deploy and maintain

---


## Privacy & Data Collection

**HomeSentry collects ZERO data from users.**

- ✅ All monitoring data stays on YOUR server in YOUR SQLite database
- ✅ No phone-home, no telemetry, no analytics
- ✅ Discord webhook is YOUR webhook (we never see your data)
- ✅ Open source - audit the code yourself
- ✅ Designed for self-hosting and complete privacy

Your data never leaves your network unless you configure it to (via Discord alerts, which go directly from your server to Discord).

---

## Quick Start

### Prerequisites

- Linux server (Ubuntu, Debian, or similar)
- Docker and Docker Compose installed
- Discord webhook URL (for alerts)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/homesentry.git
   cd homesentry
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Edit `.env` with your settings:
   ```ini
   # Discord webhook for alerts
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   
   # Services to monitor
   PLEX_URL=http://localhost:32400
   JELLYFIN_URL=http://localhost:8096
   
   # Thresholds
   DISK_FREE_PERCENT_WARN=15
   DISK_FREE_GB_WARN=50
   ```

3. **Start HomeSentry:**
   ```bash
   docker compose up -d
   ```

4. **Access the dashboard:**
   
   Open your browser to `http://your-server-ip:8000`

---

## Architecture

HomeSentry is built with modularity and resilience in mind:

```
┌─────────────────────────────────────────┐
│         FastAPI Web Server              │
│  (Dashboard + JSON API + Healthcheck)   │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        │   Scheduler   │  (Background polling)
        └───────┬───────┘
                │
    ┌───────────┼───────────┐
    │           │           │
┌───▼───┐   ┌──▼──┐   ┌───▼────┐
│System │   │SMART│   │Services│  ... (Collectors)
└───┬───┘   └──┬──┘   └───┬────┘
    │          │          │
    └──────────┼──────────┘
               │
        ┌──────▼──────┐
        │   SQLite    │  (Metrics + Events)
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Alerting  │  (Discord webhook)
        └─────────────┘
```

### Core Components

- **Collectors** - Independent modules that gather metrics (system, disk, SMART, Docker, services, RAID)
- **Storage** - SQLite database for metrics history and events
- **Scheduler** - Background task loop that runs collectors every N seconds
- **Alerting** - Discord webhook integration with state-change logic (avoids spam)
- **Web Server** - FastAPI serving dashboard + JSON API

Each collector is self-contained and failure-resistant—if one fails, the others keep running.

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_WEBHOOK_URL` | Discord webhook for alerts | *(required)* |
| `POLL_INTERVAL` | Seconds between checks | `60` |
| `SMART_POLL_INTERVAL` | Seconds between SMART checks | `600` |
| `PLEX_URL` | Plex server URL | - |
| `JELLYFIN_URL` | Jellyfin server URL | - |
| `DISK_FREE_PERCENT_WARN` | Disk free % warning threshold | `15` |
| `DISK_FREE_GB_WARN` | Disk free GB warning threshold | `50` |
| `CONTAINER_RESTART_THRESHOLD` | Restart count warning | `5` |

### Monitored Services

HomeSentry can monitor any HTTP service. Add URLs to `.env`:

```ini
PLEX_URL=http://localhost:32400
JELLYFIN_URL=http://localhost:8096
PIHOLE_URL=http://localhost:80
```

---

## API Endpoints

HomeSentry exposes a JSON API for integration:

### `GET /`
Returns HTML dashboard

### `GET /api/status`
Returns current status summary:
```json
{
  "last_updated": "2026-01-25T12:00:00Z",
  "categories": {
    "storage": "OK",
    "media": "OK",
    "docker": "WARN",
    "network": "OK"
  },
  "details": { ... }
}
```

### `GET /api/metrics?hours=24`
Returns time-series metrics for the last N hours

### `GET /api/events?limit=50`
Returns recent state-change events

### `GET /healthz`
Liveness check (always returns `200 OK` if server is running)

---

## Development

HomeSentry is designed as a **learning project** that's also **genuinely useful**. The code is readable, well-commented, and structured to be extended easily.

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run locally:**
   ```bash
   cd app
   python -m uvicorn main:app --reload
   ```

3. **Access dashboard:**
   ```
   http://localhost:8000
   ```

### Project Structure

```
homesentry/
├── app/
│   ├── main.py              # FastAPI application
│   ├── collectors/          # Monitoring modules
│   │   ├── system.py
│   │   ├── smart.py
│   │   ├── docker.py
│   │   ├── services.py
│   │   └── raid.py
│   ├── storage/             # Database layer
│   │   ├── db.py
│   │   └── models.py
│   ├── alerts/              # Notification system
│   │   ├── discord.py
│   │   └── rules.py
│   └── templates/           # HTML templates
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/                   # Unit tests
└── scripts/                 # Utility scripts
```

### Adding a New Collector

1. Create `app/collectors/your_collector.py`
2. Implement a `collect()` function that returns a standardized result
3. Register it in the scheduler
4. Done!

Example collector:
```python
def collect() -> dict:
    """Collect metrics for this check."""
    try:
        # Your collection logic here
        value = get_some_metric()
        
        # Determine status
        if value > threshold:
            status = "FAIL"
        elif value > warning:
            status = "WARN"
        else:
            status = "OK"
        
        return {
            "status": status,
            "value": value,
            "details": {"extra": "info"}
        }
    except Exception as e:
        return {
            "status": "FAIL",
            "error": str(e)
        }
```

---

## Deployment

### Docker Compose (Recommended)

The provided `docker-compose.yml` handles everything:

```yaml
services:
  homesentry:
    build: ./docker
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data          # Database persistence
      - /proc:/host/proc:ro   # Host CPU/RAM metrics
      - /sys:/host/sys:ro     # Host disk metrics
    env_file:
      - .env
    restart: unless-stopped
```

### Systemd Service (Alternative)

If you prefer running without Docker:

1. Install Python dependencies: `pip install -r requirements.txt`
2. Create systemd service file: `/etc/systemd/system/homesentry.service`
3. Enable and start: `systemctl enable --now homesentry`

---

## Roadmap

### v0.1.0 (January 25, 2026) ✅ Shipped
- [x] FastAPI web server
- [x] System monitoring (CPU, RAM, disk)
- [x] Service HTTP checks
- [x] SQLite storage
- [x] Background scheduler (autonomous monitoring)
- [x] Discord alerts
- [x] Docker deployment
- [x] Basic dashboard UI

### v0.2.0 (January 27, 2026) ✅ Shipped
- [x] Docker container monitoring
- [x] SMART health checks
- [x] RAID status monitoring
- [x] Enhanced scheduler with multi-frequency collection
- [x] Critical infrastructure alerting

### v0.3.0 (January 31, 2026) ✅ Shipped
- [x] Plugin architecture (AppModule base class, auto-discovery)
- [x] Home Assistant monitoring module
- [x] qBittorrent monitoring module
- [x] Pi-hole monitoring module
- [x] Plex monitoring module
- [x] Jellyfin monitoring module
- [x] Maintenance windows and sleep schedule
- [x] Dashboard two-layer UI with dark mode
- [x] Bare-metal module support

### v0.4.0 (February 1, 2026) ✅ Shipped
- [x] Polish release — 22 fixes across code quality, configuration, and documentation

### v0.5.0 (February 10, 2026) ✅ Shipped
- [x] Interactive installation wizard (TUI setup with auto-detection)
- [x] Web-based configuration UI (/config page)
- [x] Browser-based module enable/disable toggles
- [x] Bare-metal service support (Plex, Pi-hole)
- [x] Immediate configuration updates without restart

### v0.6.0 (February 13, 2026) ✅ Shipped
- [x] Sustained state checking (grace period for transient flaps)
- [x] Fixed duplicate morning summaries
- [x] Fixed morning summary timestamps (12-hour with AM/PM)
- [x] Fixed maintenance window filtering in sleep schedule
- [x] Security: Removed .env from Git tracking and history

### v0.7.0 (February 16, 2026) ✅ Shipped
- [x] Historical Trends section in dashboard with Chart.js 4.4.1
- [x] Bucketed time-series API (`/api/metrics/history`)
- [x] Dynamic chart metric discovery (`/api/metrics/history/available`)
- [x] 2-column chart grid with 6h / 24h / 7d time range selector
- [x] Dark mode chart colors with CSS variable support

### v0.8.0 (February 2026) ✅ Shipped
- [x] Docs catch-up — version strings, README roadmap, CHANGELOG summary all updated to reflect shipped state
- [x] Data retention — nightly cleanup job for `metrics_samples` with `METRICS_RETENTION_DAYS` config
- [x] Dashboard UX improvements — footer version, chart empty-state handling

### v1.0.0 (Future)
- [ ] Authentication
- [ ] Mobile-responsive UI
- [ ] Multi-server support

---

## Troubleshooting

### Dashboard shows "Service Unreachable"
- Check that the service URL is correct in `.env`
- Verify the service is actually running
- Test the URL manually: `curl http://your-service-url`

### No Discord alerts
- Verify `DISCORD_WEBHOOK_URL` is set correctly
- Check HomeSentry logs: `docker compose logs -f`
- Test the webhook manually

### SMART checks not working
- Ensure Docker container has access to `/dev` devices
- Run `smartctl` on host to verify drives support SMART

### Container keeps restarting
- Check logs: `docker compose logs homesentry`
- Verify `.env` file exists and is valid
- Check for port conflicts (port 8000)

---

## Contributing

Contributions are welcome! This is a learning project, so don't be shy about asking questions or proposing ideas.

### Guidelines:
- Follow existing code style (Black formatting)
- Add comments explaining WHY, not just WHAT
- Test on real hardware when possible
- Update documentation for new features

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Inspired by Pi-hole's installation UX
- Built as a portfolio/learning project
- Designed for real-world use on actual home servers

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/homesentry/issues)
- **Documentation**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Remember**: HomeSentry is your server's watchdog. Set it up once, then relax knowing you'll be alerted if anything goes wrong. 🐕‍🦺
