# HomeSentry Module Development Guide

This guide covers everything you need to write a new app module for HomeSentry. The architecture is designed so that creating a module takes about 15 minutes — one file, a few environment variables, and it starts appearing on the dashboard automatically.

---

## How it works

The module system has four moving parts, and you only need to touch one of them:

**1. Auto-discovery** — At startup, HomeSentry scans the `app/collectors/modules/` directory for Python files. Any file that defines a class inheriting from `AppModule` is automatically loaded. There is no registry to update, no configuration file to edit. Drop a `.py` file in that directory, and it exists.

**2. Container matching** — Once discovered, the module runner checks every running Docker container against each module's `CONTAINER_NAMES` list. When a container name matches, that module's `collect()` method runs against it. If you set `{APP_NAME}_BARE_METAL=true` in your `.env`, the container-matching step is skipped entirely and `collect()` runs with `container=None`.

**3. Configuration parsing** — All module configuration comes from environment variables. The framework automatically scans for variables prefixed with `{APP_NAME}_` (uppercased), strips the prefix, lowercases the key, and converts the value to the appropriate Python type. Your `collect()` method receives the result as a plain `dict`.

**4. The module itself** — This is the only piece you write. It defines three class attributes and implements one method. The framework handles everything else: storing metrics to the database, processing alerts against thresholds, enforcing hard limits, and isolating errors so a broken module can't crash the system.

---

## What every module must define

```python
from app.collectors.modules.base import AppModule
import aiohttp
import logging

logger = logging.getLogger(__name__)


class MyAppModule(AppModule):
    """Monitor My App."""

    # 1. Unique identifier — lowercase, no spaces or hyphens.
    #    This becomes the environment variable prefix (MYAPP_...)
    #    and the metric name prefix in the database (myapp_...).
    APP_NAME = "myapp"

    # 2. Human-friendly name shown on the dashboard card.
    APP_DISPLAY_NAME = "My App"

    # 3. Docker container names this module should match against.
    #    The module runner checks running containers and activates
    #    this module when any of these names match.
    CONTAINER_NAMES = ["myapp", "my-app"]

    # 4. The only method you must implement.
    async def collect(self, container, config: dict) -> dict:
        """
        Collect metrics from the application.

        Args:
            container: Docker container object, or None if running bare-metal.
            config:    Dict of settings parsed from environment variables.

        Returns:
            Dict of {metric_name: value}. Keys are lowercase with underscores.
            Values are int, float, or str.
        """
        api_url = config.get("api_url", "")
        timeout = config.get("timeout", 10)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/api/status",
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"My App API returned {resp.status}")
                        return {}

                    data = await resp.json()

            return {
                "total_items": data.get("total_items", 0),
                "active_users": data.get("active_users", 0),
            }

        except aiohttp.ClientError as e:
            logger.error(f"Failed to collect from My App: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in My App module: {e}")
            return {}
```

That is the complete interface. `validate_config()` is optional — override it if you want to check that required config values are present before `collect()` runs.

---

## Hard limits

The framework enforces these automatically. If a module exceeds them, the runner truncates or logs a warning — it does not crash.

| Limit | Value | Why |
|-------|-------|-----|
| Max metrics returned per collection | 10 | Keeps dashboard cards scannable |
| Max API calls per collection cycle | 3 | Prevents slow collections from blocking the scheduler |
| Max config options | 15 | Keeps `.env` manageable |

The API call limit is a design guideline rather than a runtime counter — the framework trusts you to stay within it. The metric and config limits are enforced by truncation in `module_runner.py`.

---

## Configuration convention

All configuration is driven by environment variables. No config files, no YAML, no JSON — just entries in `.env`.

The framework automatically parses any variable that starts with your module's `APP_NAME` (uppercased) followed by an underscore:

```
MYAPP_API_URL=http://myapp:8080      →  config["api_url"]        = "http://myapp:8080"
MYAPP_TIMEOUT=10                     →  config["timeout"]        = 10
MYAPP_ENABLED=true                   →  config["enabled"]        = True
MYAPP_SOME_THRESHOLD=3.5             →  config["some_threshold"] = 3.5
MYAPP_BARE_METAL=true                →  config["bare_metal"]     = True
```

Type conversion is automatic: `"true"`/`"false"` become `bool`, plain integers become `int`, numbers with a decimal point become `float`, everything else stays as `str`.

**Thresholds for alerting** follow a specific naming pattern. If you have a metric called `queue_size`, the framework looks for `MYAPP_QUEUE_SIZE_WARN` and `MYAPP_QUEUE_SIZE_FAIL` in the config dict (as `queue_size_warn` and `queue_size_fail`). When the metric value reaches or exceeds those thresholds, the alert system fires a Discord notification on the first state change.

---

## Bare-metal support

Some services run as systemd services rather than Docker containers. On this server, Plex and Pi-hole are both bare-metal examples. The module system handles this transparently.

To enable bare-metal mode for a module, add this to `.env`:

```
MYAPP_BARE_METAL=true
```

When the module runner sees `bare_metal=true` in the parsed config, it skips container matching entirely and calls `collect()` with `container=None`. Your `collect()` method typically does not use the `container` argument anyway — it makes API calls to a URL from config — so most modules work in both modes without any code changes.

Metrics collected in bare-metal mode are stored with `"baremetal"` as the container name in the database.

---

## Step-by-step: Writing a Sonarr module

This walkthrough creates a module for Sonarr (a TV show download manager) from scratch to dashboard appearance. Sonarr is fictional here — the pattern is the same for any application with an HTTP API.

**Step 1: Create the file.**

Create `app/collectors/modules/sonarr.py`. The filename does not matter for discovery — only the class inside matters — but naming it after the app keeps things organized.

**Step 2: Define the class.**

```python
"""
Sonarr monitoring module.

Collects metrics from Sonarr via its REST API.
Tracks series count, queued downloads, and missing episodes.

Configuration:
    SONARR_API_URL: Sonarr base URL (required)
    SONARR_API_KEY: API key from Sonarr settings (required)
    SONARR_QUEUE_SIZE_WARN: Warning threshold for queued downloads
    SONARR_QUEUE_SIZE_FAIL: Critical threshold for queued downloads

Example:
    SONARR_API_URL=http://sonarr:8989
    SONARR_API_KEY=abc123def456
    SONARR_QUEUE_SIZE_WARN=10
    SONARR_QUEUE_SIZE_FAIL=25
"""
from app.collectors.modules.base import AppModule
import aiohttp
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SonarrModule(AppModule):
    """Monitor Sonarr TV download manager."""

    APP_NAME = "sonarr"
    APP_DISPLAY_NAME = "Sonarr"
    CONTAINER_NAMES = ["sonarr"]

    async def collect(self, container, config: dict) -> Dict[str, Any]:
        api_url = config.get("api_url", "").rstrip("/")
        api_key = config.get("api_key", "")
        timeout = config.get("timeout", 10)

        if not api_url or not api_key:
            logger.warning("Sonarr module missing required config")
            return {}

        headers = {"X-Api-Key": api_key}
        metrics = {}

        try:
            async with aiohttp.ClientSession() as session:
                # API Call 1: Get all series
                async with session.get(
                    f"{api_url}/api/v3/series",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Sonarr series API returned {resp.status}")
                        return {}
                    series_list = await resp.json()
                    metrics["series_count"] = len(series_list)
                    metrics["missing_episodes"] = sum(
                        s.get("episodeMissingCount", 0) for s in series_list
                    )

                # API Call 2: Get download queue
                async with session.get(
                    f"{api_url}/api/v3/queue",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        queue_data = await resp.json()
                        metrics["queue_size"] = queue_data.get("totalCount", 0)

            logger.info(
                f"Sonarr: {metrics.get('series_count', 0)} series, "
                f"{metrics.get('queue_size', 0)} queued"
            )
            return metrics

        except aiohttp.ClientError as e:
            logger.error(f"Sonarr API error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in Sonarr module: {e}")
            return {}

    def validate_config(self, config: dict) -> Tuple[bool, str]:
        if "api_url" not in config or not config["api_url"]:
            return (False, "api_url is required")
        if not config["api_url"].startswith("http"):
            return (False, "api_url must start with http:// or https://")
        if "api_key" not in config or not config["api_key"]:
            return (False, "api_key is required")
        return (True, "")
```

**Step 3: Add config to `.env.example` and `.env`.**

```ini
# --- Sonarr ---
SONARR_API_URL=http://sonarr:8989
SONARR_API_KEY=your_sonarr_api_key_here
SONARR_QUEUE_SIZE_WARN=10
SONARR_QUEUE_SIZE_FAIL=25
```

**Step 4: Register the dashboard card in `main.py`.**

Add `"sonarr"` to the three dicts in the dashboard route (see the Dashboard Card Display section below):

```python
APP_PREFIXES = [..., "sonarr"]

APP_DISPLAY_NAMES = {
    ...,
    "sonarr": "Sonarr",
}

APP_CARD_METRICS = {
    ...,
    "sonarr": ["series_count", "queue_size", "missing_episodes"],
}
```

**Step 5: Rebuild and verify.**

```bash
cd ~/git/homesentry
git pull
docker compose -f docker/docker-compose.yml up --build -d
```

The module appears in the log on startup:

```
Discovered module: Sonarr (containers: sonarr)
```

And shows up on the dashboard as a card in the Application Layer section, displaying the three metrics you specified in `APP_CARD_METRICS`.

---

## Reference: Existing modules

Each module below solved a slightly different problem — different auth schemes, response formats, and bare-metal requirements. This table lets you see at a glance how they work before you start your own.

| Module | Auth Method | API Calls/Cycle | Metrics | Mode |
|--------|-------------|-----------------|---------|------|
| Home Assistant | Bearer token (`Authorization: Bearer ...`) | 1 | entity_count, automation_count, response_time_ms | Docker |
| qBittorrent | Session cookie (login → SID cookie) | 2 (+ 1 auth) | active_torrents, download_speed_mbps, upload_speed_mbps, session_downloaded_gb, session_uploaded_gb, disk_free_gb | Docker |
| Pi-hole | Session + CSRF (login → sid cookie + csrf token) | 1 (+ 1 auth) | total_queries_today, queries_blocked_today, percent_blocked, active_clients, blocklist_size, queries_forwarded | Bare-metal |
| Plex | Header token (`X-Plex-Token`) | 2–3 | active_streams, transcode_count, bandwidth_mbps, library_items, movie_count, tv_show_count | Bare-metal |
| Jellyfin | Header token (`X-Emby-Token`) | 2 | active_streams, transcode_count, active_users, library_items, movie_count, series_count, episode_count | Docker |

A few patterns worth noting from this table. Auth that requires a login step (qBittorrent, Pi-hole) counts the login as one of your API calls — plan accordingly. Plex returns XML instead of JSON, which requires `xml.etree.ElementTree` parsing. Bare-metal modules use the exact same `collect()` signature as Docker modules; the only difference is that `container` is `None`.

---

## Dashboard card display

When you return metrics from `collect()`, the framework stores each one in the database under the `app` category with a name like `sonarr_series_count` (module prefix + metric key). The dashboard then needs to know which of those metrics to actually show on the card, and in what order.

This is controlled by three dicts in `app/main.py`, inside the dashboard route function:

```python
# Which app prefixes to look for when grouping metrics
APP_PREFIXES = ["plex", "jellyfin", "pihole", "homeassistant", "qbittorrent"]

# Display name shown at the top of each card
APP_DISPLAY_NAMES = {
    "plex": "Plex",
    "jellyfin": "Jellyfin",
    ...
}

# Which metrics appear on the card, in priority order.
# Only the first 3–4 matter — the card displays them top to bottom.
APP_CARD_METRICS = {
    "plex": ["active_streams", "transcode_count", "movie_count", "tv_show_count"],
    "jellyfin": ["active_streams", "transcode_count", "movie_count", "episode_count"],
    ...
}
```

When you add a new module, you add an entry to all three. The metric names in `APP_CARD_METRICS` must match the keys your `collect()` method returns exactly — they are the same strings, just without the module prefix.

If a metric in `APP_CARD_METRICS` has no data yet (the module hasn't collected successfully), the dashboard shows a dash for that metric rather than crashing. Once collection succeeds, the value appears on the next refresh.
