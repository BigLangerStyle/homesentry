"""
Mitch Discord Bot monitoring module.

Collects app-specific metrics from Mitch via its health endpoint.
Tracks Discord connectivity, Ollama responsiveness, uptime, and memory usage.

Mitch runs as a bare-metal systemd service (not in Docker).
Health endpoint: http://localhost:8001/health

Configuration:
    MITCH_API_URL: Health endpoint base URL (required)
    MITCH_BARE_METAL: Must be 'true' — module refuses to run without it (required)
    MITCH_TIMEOUT: API timeout in seconds (default: 5)
    MITCH_UPTIME_SECONDS_WARN: Warn if uptime is BELOW this value (seconds). A low
        uptime means the bot restarted recently. Requires the companion key
        MITCH_UPTIME_SECONDS_WARN_BELOW=true to invert the comparison direction in
        determine_metric_status(). Without that key, the comparison would be >=
        (warn when high), which is the opposite of what we want for uptime.
    MITCH_UPTIME_SECONDS_WARN_BELOW: Set to 'true' to invert the uptime_seconds
        threshold — WARN when uptime < threshold instead of >= threshold.
    MITCH_MEMORY_MB_WARN: Warning threshold for memory usage MB (default: 400)
    MITCH_MEMORY_MB_FAIL: Critical threshold for memory usage MB (default: 800)
    MITCH_DATABASE_SIZE_MB_WARN: Warning threshold for database size MB (default: 50)
    MITCH_DATABASE_SIZE_MB_FAIL: Critical threshold for database size MB (default: 100)

Example:
    MITCH_API_URL=http://localhost:8001
    MITCH_BARE_METAL=true
    MITCH_TIMEOUT=5
    MITCH_UPTIME_SECONDS_WARN=3600
    MITCH_UPTIME_SECONDS_WARN_BELOW=true
    MITCH_MEMORY_MB_WARN=400
    MITCH_MEMORY_MB_FAIL=800
"""
from app.collectors.modules.base import AppModule
import aiohttp
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MitchModule(AppModule):
    """Monitor Mitch Discord Bot bare-metal service."""

    # Module metadata
    APP_NAME = "mitch"
    APP_DISPLAY_NAME = "Mitch Bot"
    CONTAINER_NAMES = []  # Bare-metal only — no Docker container

    async def collect(self, container, config: dict) -> Dict[str, Any]:
        """
        Collect metrics from Mitch Discord Bot health endpoint.

        Makes 1 API call:
        1. GET /health - Discord connectivity, Ollama status, uptime, memory, DB size

        Args:
            container: Docker container object (None for bare-metal modules)
            config: Configuration dict with api_url, timeout, etc.

        Returns:
            Dict of metrics: discord_connected, ollama_responsive, uptime_seconds,
            memory_mb, database_size_mb
        """
        api_url = config.get('api_url', '').rstrip('/')
        timeout = config.get('timeout', 5)

        if not api_url:
            logger.warning("Mitch module missing required config: api_url")
            return {}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Mitch health endpoint returned HTTP {resp.status}")
                        return {"status": "unreachable"}

                    data = await resp.json()

            # Extract metrics — store booleans as int (0/1)
            discord = data.get('discord', {})
            ollama = data.get('ollama', {})
            database = data.get('database', {})

            metrics = {
                'discord_connected': int(bool(discord.get('connected', False))),
                'ollama_responsive': int(bool(ollama.get('responsive', False))),
                'uptime_seconds': data.get('uptime_seconds', 0),
                'memory_mb': data.get('memory_mb', 0.0),
                'database_size_mb': database.get('size_mb', 0.0),
            }

            logger.info(
                f"Mitch metrics: discord={'connected' if metrics['discord_connected'] else 'disconnected'}, "
                f"ollama={'ok' if metrics['ollama_responsive'] else 'down'}, "
                f"uptime={metrics['uptime_seconds']}s, memory={metrics['memory_mb']}MB"
            )

            return metrics

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Mitch health endpoint unreachable: {e}")
            return {"status": "unreachable"}

        except Exception as e:
            logger.error(f"Unexpected error in Mitch module: {e}", exc_info=True)
            return {"status": "error"}

    def validate_config(self, config: dict) -> tuple[bool, str]:
        """
        Validate Mitch configuration.

        Checks:
        - bare_metal is truthy (Mitch is always bare-metal)
        - api_url is present and valid

        Args:
            config: Configuration dict

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Mitch is bare-metal only — refuse to run without this flag
        if not config.get('bare_metal'):
            return (False, "MITCH_BARE_METAL must be set to 'true' — Mitch runs as a systemd service, not in Docker")

        # Check api_url
        if 'api_url' not in config:
            return (False, "MITCH_API_URL is required")

        api_url = config['api_url']
        if not api_url.startswith('http://') and not api_url.startswith('https://'):
            return (False, "MITCH_API_URL must start with http:// or https://")

        return (True, "")
