# Changelog

All notable changes to HomeSentry will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-dev] - 2026-01-25

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

### Planned for v0.1.0 MVP
- FastAPI web server with HTML dashboard
- System collector (CPU, RAM, disk usage)
- Service HTTP health checks (Plex, Jellyfin)
- SQLite database schema
- Discord webhook alerting
- Docker deployment configuration
- Basic HTML/CSS dashboard UI

---

## Version History Summary

- **v0.1.0-dev** (Current) - Initial setup and MVP development
- **v0.2.0** (Planned) - Docker monitoring + SMART checks + RAID status
- **v0.5.0** (Future) - Interactive installer + modular collectors
- **v1.0.0** (Future) - Historical charts + authentication + UI polish
