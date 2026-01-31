"""
HomeSentry - FastAPI application entry point

This module sets up the FastAPI application with basic endpoints,
logging configuration, and CORS middleware.
"""
import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.storage import (
    init_database,
    get_latest_metrics,
    get_latest_service_status,
    get_latest_events,
)
from app.collectors import (
    collect_all_system_metrics,
    check_all_services,
    collect_all_docker_metrics,
    collect_all_smart_metrics,
    collect_all_raid_metrics,
    collect_all_app_metrics,
)
from app.collectors.modules import get_discovered_modules
from app.scheduler import run_scheduler

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application instance
app = FastAPI(
    title="HomeSentry",
    description="Home server health monitoring dashboard",
    version="0.1.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc",  # ReDoc at /redoc
)

# Configure CORS middleware (allow all origins for now - security comes in v1.0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Global task reference for scheduler
scheduler_task = None


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    Logs startup information and configuration, initializes the database,
    and starts the background scheduler for autonomous monitoring.
    """
    global scheduler_task
    
    logger.info("=" * 60)
    logger.info("HomeSentry v0.1.0 starting up...")
    logger.info("=" * 60)
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Database path: {os.getenv('DATABASE_PATH', '/app/data/homesentry.db')}")
    logger.info(f"Poll interval: {os.getenv('POLL_INTERVAL', '60')}s")
    
    # Initialize database
    try:
        db_success = await init_database()
        if db_success:
            logger.info("Database initialized successfully ✓")
        else:
            logger.error("Database initialization failed - check logs above")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        # Don't crash - app can still serve endpoints
    
    # Check if Discord webhook is configured
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_webhook and discord_webhook != "https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE":
        logger.info("Discord webhook: configured ✓")
    else:
        logger.warning("Discord webhook: not configured (alerts disabled)")
    
    # Start background scheduler
    logger.info("Starting background scheduler...")
    scheduler_task = asyncio.create_task(run_scheduler())
    logger.info("Scheduler task created ✓")
    
    logger.info("=" * 60)
    logger.info("Application started successfully!")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    Stops the background scheduler gracefully and logs shutdown information.
    """
    global scheduler_task
    
    logger.info("=" * 60)
    logger.info("HomeSentry shutting down...")
    logger.info("=" * 60)
    
    if scheduler_task:
        logger.info("Stopping scheduler...")
        scheduler_task.cancel()
        try:
            await asyncio.wait_for(scheduler_task, timeout=10)
            logger.info("Scheduler stopped cleanly ✓")
        except asyncio.TimeoutError:
            logger.warning("Scheduler shutdown timed out")
        except asyncio.CancelledError:
            logger.info("Scheduler cancelled ✓")
    
    logger.info("Shutdown complete")


# Helper functions for dashboard data processing
def process_system_status(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract latest system metrics for dashboard display.
    
    Args:
        metrics: List of metric samples from database
        
    Returns:
        Dict with processed system status (CPU, memory, disk)
    """
    status = {
        "cpu": {"value": "N/A", "status": "UNKNOWN"},
        "memory": {"value": "N/A", "status": "UNKNOWN"},
        "disk": []
    }
    
    for metric in metrics:
        if metric["category"] == "system":
            if "cpu_percent" in metric["name"]:
                status["cpu"] = {
                    "value": f"{metric['value_num']:.1f}%",
                    "status": metric["status"]
                }
            elif "memory_percent" in metric["name"]:
                status["memory"] = {
                    "value": f"{metric['value_num']:.1f}%",
                    "status": metric["status"]
                }
        elif metric["category"] == "disk":
            # Extract mountpoint from name like "disk_/mnt/Array_percent"
            name = metric["name"].replace("disk_", "").replace("_percent", "")
            status["disk"].append({
                "mountpoint": name,
                "value": f"{metric['value_num']:.1f}%",
                "status": metric["status"]
            })
    
    return status


def process_service_status(services: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Extract latest service status for dashboard display.
    
    Args:
        services: List of service status checks from database
        
    Returns:
        Dict mapping service names to their latest status
    """
    status = {}
    
    # Get the latest status for each unique service
    seen_services = set()
    for service in services:
        service_name = service["service"]
        if service_name not in seen_services:
            status[service_name] = {
                "status": service["status"],
                "response_ms": service["response_ms"],
                "http_code": service["http_code"]
            }
            seen_services.add(service_name)
    
    return status


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Render the main dashboard with current system status and recent alerts.
    
    This endpoint replaces the old JSON root endpoint with a visual HTML dashboard.
    It queries the latest metrics, service status, and events from the database
    and renders them using the Jinja2 template.
    
    Args:
        request: FastAPI request object (required for Jinja2 templating)
        
    Returns:
        HTMLResponse: Rendered dashboard HTML
    """
    # Get poll interval for display
    poll_interval = os.getenv("POLL_INTERVAL", "60")
    
    # Query latest data from database
    try:
        # Get latest metrics (last 20 to find most recent of each type)
        latest_metrics_raw = await get_latest_metrics(limit=20)
        
        # Get latest service status (last 20 to find most recent of each service)
        latest_services_raw = await get_latest_service_status(limit=20)
        
        # Get recent events for alerts section
        recent_events = await get_latest_events(limit=20)
        
    except Exception as e:
        logger.error(f"Dashboard data query failed: {e}", exc_info=True)
        # Provide empty data on error - dashboard will show "no data" state
        latest_metrics_raw = []
        latest_services_raw = []
        recent_events = []
    
    # Process data for dashboard display
    system_status = process_system_status(latest_metrics_raw)
    service_status = process_service_status(latest_services_raw)
    
    # Limit metrics displayed in the table to 10 most recent
    latest_metrics = latest_metrics_raw[:10] if latest_metrics_raw else []
    
    # Render dashboard template
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "system_status": system_status,
            "service_status": service_status,
            "latest_metrics": latest_metrics,
            "recent_events": recent_events,
            "poll_interval": poll_interval,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )


@app.get("/api/metrics/latest")
async def get_latest_dashboard_metrics():
    """
    Get the latest metrics for both Application Layer and Infrastructure Layer.

    This endpoint is called by the dashboard JavaScript every 60 seconds to
    refresh the display. It returns app metrics grouped by module, plus the
    latest infrastructure metrics (system, docker, smart, raid, services).

    The app metrics are fetched from metrics_samples where category='app',
    grouped by the app prefix in the metric name (e.g., 'plex_active_streams'
    groups under 'plex').

    Returns:
        dict with keys: apps, system, docker, smart, raid, services, timestamp
    """
    # Known app module prefixes - used to group app metrics by module
    APP_PREFIXES = ["plex", "jellyfin", "pihole", "homeassistant", "qbittorrent"]

    # Human-friendly display names for each app module
    APP_DISPLAY_NAMES = {
        "plex": "Plex",
        "jellyfin": "Jellyfin",
        "pihole": "Pi-hole",
        "homeassistant": "Home Assistant",
        "qbittorrent": "qBittorrent",
    }

    # Which metrics to show on each app's dashboard card (priority order)
    APP_CARD_METRICS = {
        "plex": ["active_streams", "transcode_count", "movie_count", "tv_show_count"],
        "jellyfin": ["active_streams", "transcode_count", "movie_count", "episode_count"],
        "pihole": ["percent_blocked", "queries_blocked_today", "active_clients", "blocklist_size"],
        "homeassistant": ["entity_count", "automation_count", "response_time_ms"],
        "qbittorrent": ["download_speed_mbps", "upload_speed_mbps", "active_torrents", "disk_free_gb"],
    }

    try:
        # --- Fetch app metrics (category='app') ---
        app_metrics_raw = await get_latest_metrics(category="app", limit=100)

        # Group app metrics by module prefix, keeping only the latest per metric name
        apps = {}
        seen_metrics = set()  # Track which metrics we've already seen (dedupe by name)

        for metric in app_metrics_raw:
            name = metric["name"]
            if name in seen_metrics:
                continue  # Already have the latest sample for this metric
            seen_metrics.add(name)

            # Determine which app this metric belongs to by matching prefix
            matched_app = None
            for prefix in APP_PREFIXES:
                if name.startswith(f"{prefix}_"):
                    matched_app = prefix
                    break

            if not matched_app:
                continue  # Skip metrics with unknown prefix

            # Initialize app entry if first metric for this app
            if matched_app not in apps:
                apps[matched_app] = {
                    "name": matched_app,
                    "display_name": APP_DISPLAY_NAMES.get(matched_app, matched_app),
                    "status": "OK",
                    "metrics": {},
                    "card_metrics": APP_CARD_METRICS.get(matched_app, []),
                }

            # Strip the app prefix to get the bare metric name
            # e.g., "plex_active_streams" -> "active_streams"
            bare_name = name[len(matched_app) + 1:]

            apps[matched_app]["metrics"][bare_name] = {
                "value": metric["value_num"] if metric["value_num"] is not None else metric["value_text"],
                "status": metric["status"],
                "ts": metric["ts"],
            }

            # Bubble up worst status: OK < WARN < FAIL
            current_app_status = apps[matched_app]["status"]
            metric_status = metric["status"]
            if metric_status == "FAIL":
                apps[matched_app]["status"] = "FAIL"
            elif metric_status == "WARN" and current_app_status != "FAIL":
                apps[matched_app]["status"] = "WARN"

        # --- Fetch infrastructure metrics ---
        infra_metrics_raw = await get_latest_metrics(limit=60)
        latest_services_raw = await get_latest_service_status(limit=20)

        # Process system/disk metrics using existing helper
        system_status = process_system_status(infra_metrics_raw)
        service_status = process_service_status(latest_services_raw)

        # Extract docker container metrics (latest per container)
        docker_containers = {}
        for metric in infra_metrics_raw:
            if metric["category"] == "docker":
                parts = metric["name"].split("_", 2)
                if len(parts) >= 3:
                    container = parts[1]
                    metric_type = parts[2]
                    if container not in docker_containers:
                        docker_containers[container] = {"name": container, "status": "OK"}
                    docker_containers[container][metric_type] = metric["value_num"] if metric["value_num"] is not None else metric["value_text"]
                    if metric["status"] == "FAIL":
                        docker_containers[container]["status"] = "FAIL"
                    elif metric["status"] == "WARN" and docker_containers[container]["status"] != "FAIL":
                        docker_containers[container]["status"] = "WARN"

        # Extract SMART drive metrics (latest per drive)
        smart_drives = {}
        for metric in infra_metrics_raw:
            if metric["category"] == "smart":
                parts = metric["name"].split("_", 2)
                if len(parts) >= 3:
                    drive = parts[1]
                    metric_type = parts[2]
                    if drive not in smart_drives:
                        smart_drives[drive] = {"name": drive, "status": "OK"}
                    smart_drives[drive][metric_type] = metric["value_num"] if metric["value_num"] is not None else metric["value_text"]
                    if metric["status"] == "FAIL":
                        smart_drives[drive]["status"] = "FAIL"
                    elif metric["status"] == "WARN" and smart_drives[drive]["status"] != "FAIL":
                        smart_drives[drive]["status"] = "WARN"

        # Extract RAID array metrics (latest per array)
        raid_arrays = {}
        for metric in infra_metrics_raw:
            if metric["category"] == "raid":
                parts = metric["name"].split("_", 2)
                if len(parts) >= 3:
                    array = parts[1]
                    metric_type = parts[2]
                    if array not in raid_arrays:
                        raid_arrays[array] = {"name": array, "status": "OK"}
                    raid_arrays[array][metric_type] = metric["value_num"] if metric["value_num"] is not None else metric["value_text"]
                    if metric["status"] == "FAIL":
                        raid_arrays[array]["status"] = "FAIL"
                    elif metric["status"] == "WARN" and raid_arrays[array]["status"] != "FAIL":
                        raid_arrays[array]["status"] = "WARN"

        return {
            "apps": apps,
            "system": system_status,
            "docker": list(docker_containers.values()),
            "smart": list(smart_drives.values()),
            "raid": list(raid_arrays.values()),
            "services": service_status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get latest dashboard metrics: {e}", exc_info=True)
        return {
            "apps": {},
            "system": {"cpu": {"value": "N/A", "status": "UNKNOWN"}, "memory": {"value": "N/A", "status": "UNKNOWN"}, "disk": []},
            "docker": [],
            "smart": [],
            "raid": [],
            "services": {},
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


@app.get("/api/dashboard/status")
async def dashboard_status_api():
    """
    Get current system and service status as JSON.
    
    This API endpoint provides the same data as the visual dashboard but in JSON format,
    useful for programmatic access or building custom dashboards.
    
    Returns:
        dict: Current status of all monitored systems and services
    """
    try:
        latest_metrics_raw = await get_latest_metrics(limit=20)
        latest_services_raw = await get_latest_service_status(limit=20)
        
        system_status = process_system_status(latest_metrics_raw)
        service_status = process_service_status(latest_services_raw)
        
        return {
            "system": system_status,
            "services": service_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard status API failed: {e}", exc_info=True)
        return {
            "error": "Failed to retrieve status",
            "system": {"cpu": {"value": "N/A", "status": "UNKNOWN"}, "memory": {"value": "N/A", "status": "UNKNOWN"}, "disk": []},
            "services": {},
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/dashboard/events")
async def dashboard_events_api(limit: int = 20):
    """
    Get recent events/alerts as JSON.
    
    This API endpoint provides recent alert events in JSON format for programmatic access.
    
    Args:
        limit: Maximum number of events to return (default: 20, max: 100)
        
    Returns:
        dict: List of recent events with metadata
    """
    # Clamp limit to reasonable range
    limit = max(1, min(limit, 100))
    
    try:
        recent_events = await get_latest_events(limit=limit)
        return {
            "events": recent_events,
            "count": len(recent_events),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard events API failed: {e}", exc_info=True)
        return {
            "error": "Failed to retrieve events",
            "events": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }


@app.get("/healthz")
async def health_check():
    """
    Health check endpoint for Docker and monitoring systems.
    
    This endpoint is used by Docker's HEALTHCHECK directive and
    can be used by external monitoring systems to verify the
    application is running correctly.
    
    Returns:
        dict: Simple health status
    """
    return {"status": "healthy"}


@app.get("/api/collect/system")
async def manual_collect_system():
    """
    Manually trigger system metrics collection (for testing).
    
    Collects CPU, memory, and disk metrics and writes them to the database.
    Useful for testing the system collector before scheduling is implemented.
    
    Returns:
        dict: Collection results with all metrics and status
    """
    logger.info("Manual system metrics collection triggered via API")
    results = await collect_all_system_metrics()
    return {
        "message": "System metrics collected successfully",
        "results": results,
    }



@app.get("/api/collect/services")
async def manual_collect_services():
    """
    Manually trigger service health checks (for testing).
    
    Checks all configured services (Plex, Jellyfin, Pi-hole, etc.) via HTTP,
    measures response times, and writes results to the database.
    Useful for testing the service collector before scheduling is implemented.
    
    Returns:
        dict: Collection results with all service check results and status
    """
    logger.info("Manual service health checks triggered via API")
    results = await check_all_services()
    return {
        "message": "Service checks completed",
        "results": results,
    }

@app.get("/api/collect/docker")
async def manual_collect_docker():
    """
    Manually trigger Docker container metrics collection (for testing).
    
    Collects container status, health checks, restart counts, and resource usage
    for all Docker containers on the host system. Writes results to the database.
    Useful for testing the Docker collector before scheduling is implemented.
    
    Returns:
        dict: Collection results with all container metrics and status
    """
    from app.collectors import collect_all_docker_metrics
    
    logger.info("Manual Docker metrics collection triggered via API")
    results = await collect_all_docker_metrics()
    return {
        "message": "Docker metrics collected successfully",
        "results": results,
    }

@app.get("/api/collect/smart")
async def manual_collect_smart():
    """
    Manually trigger SMART drive health metrics collection (for testing).
    
    Collects SMART health status, temperature, and critical attributes
    (reallocated sectors, pending sectors, power-on hours) for all configured
    drives. Writes results to the database.
    Useful for testing the SMART collector before scheduling is implemented.
    
    Returns:
        dict: Collection results with all drive SMART metrics and status
    """
    logger.info("Manual SMART metrics collection triggered via API")
    results = await collect_all_smart_metrics()
    return {
        "message": "SMART metrics collected successfully",
        "results": results,
    }

@app.get("/api/collect/raid")
async def manual_collect_raid():
    """
    Manually trigger RAID array metrics collection (for testing).
    
    Collects RAID array status, disk health, and rebuild progress for all
    configured mdadm arrays. Writes results to the database.
    Useful for testing the RAID collector before scheduling is implemented.
    
    Returns:
        dict: Collection results with all RAID array metrics and status
    """
    logger.info("Manual RAID metrics collection triggered via API")
    results = await collect_all_raid_metrics()
    return {
        "message": "RAID metrics collected successfully",
        "results": results,
    }

@app.get("/api/modules")
async def list_modules():
    """
    List all discovered app modules.
    
    Returns information about all available monitoring modules including
    their metadata, supported containers, and current status. Modules are
    automatically discovered from the app/collectors/modules/ directory.
    
    Returns:
        dict: List of modules with their metadata and configuration
        
    Example response:
        {
            "modules": [
                {
                    "name": "homeassistant",
                    "display_name": "Home Assistant",
                    "container_names": ["homeassistant", "hass"],
                    "max_metrics": 10,
                    "max_api_calls": 3,
                    "max_config_options": 15
                }
            ]
        }
    """
    logger.info("Module list requested via API")
    modules = get_discovered_modules()
    
    module_list = []
    for module_class in modules:
        module_list.append({
            "name": module_class.APP_NAME,
            "display_name": module_class.APP_DISPLAY_NAME,
            "container_names": module_class.CONTAINER_NAMES,
            "max_metrics": module_class.MAX_METRICS,
            "max_api_calls": module_class.MAX_API_CALLS,
            "max_config_options": module_class.MAX_CONFIG_OPTIONS,
        })
    
    return {
        "count": len(module_list),
        "modules": module_list
    }

@app.get("/api/modules/{app_name}")
async def get_module_details(app_name: str):
    """
    Get details for a specific module.
    
    Returns detailed information about a specific app monitoring module
    including its configuration, capabilities, and current status.
    
    Args:
        app_name: Module app name (e.g., "homeassistant", "qbittorrent")
    
    Returns:
        dict: Module metadata and details
        
    Example response:
        {
            "name": "homeassistant",
            "display_name": "Home Assistant",
            "container_names": ["homeassistant", "hass"],
            "limits": {
                "max_metrics": 10,
                "max_api_calls": 3,
                "max_config_options": 15
            }
        }
    """
    logger.info(f"Module details requested for: {app_name}")
    modules = get_discovered_modules()
    
    # Find the requested module
    for module_class in modules:
        if module_class.APP_NAME == app_name:
            return {
                "name": module_class.APP_NAME,
                "display_name": module_class.APP_DISPLAY_NAME,
                "container_names": module_class.CONTAINER_NAMES,
                "limits": {
                    "max_metrics": module_class.MAX_METRICS,
                    "max_api_calls": module_class.MAX_API_CALLS,
                    "max_config_options": module_class.MAX_CONFIG_OPTIONS,
                }
            }
    
    # Module not found
    return {
        "error": f"Module '{app_name}' not found",
        "available_modules": [m.APP_NAME for m in modules]
    }

@app.get("/api/collect/modules")
async def manual_collect_all_modules():
    """
    Manually trigger collection for all app modules (for testing).
    
    Discovers all available app modules, matches them to running containers,
    and collects app-specific metrics. Writes results to the database and
    processes alerts for status changes.
    
    Useful for testing module collection and debugging module behavior.
    
    Returns:
        dict: Collection results for all modules with execution details
        
    Example response:
        {
            "message": "App module metrics collected successfully",
            "results": {
                "homeassistant_homeassistant": {
                    "status": "success",
                    "metrics": {
                        "entity_count": 342,
                        "automation_count": 45
                    },
                    "execution_time_ms": 234.56
                }
            }
        }
    """
    logger.info("Manual app module collection triggered via API")
    results = await collect_all_app_metrics()
    return {
        "message": "App module metrics collected successfully",
        "count": len(results),
        "results": results,
    }

@app.get("/api/collect/modules/{app_name}")
async def manual_collect_specific_module(app_name: str):
    """
    Manually trigger collection for a specific module (for testing).
    
    Collects metrics from a single specified app module if it's available
    and has matching running containers. Useful for testing individual
    module implementations.
    
    Args:
        app_name: Module app name (e.g., "homeassistant", "qbittorrent")
    
    Returns:
        dict: Collection results for the specified module
        
    Example response:
        {
            "message": "Module homeassistant collected successfully",
            "module": "homeassistant",
            "results": {
                "status": "success",
                "metrics": {...}
            }
        }
    """
    logger.info(f"Manual collection triggered for module: {app_name}")
    
    # Get all results and filter for the requested module
    all_results = await collect_all_app_metrics()
    
    # Find results matching this app name
    matching_results = {
        key: value for key, value in all_results.items()
        if key.startswith(f"{app_name}_")
    }
    
    if not matching_results:
        modules = get_discovered_modules()
        available = [m.APP_NAME for m in modules]
        return {
            "error": f"No results for module '{app_name}'",
            "reason": "Module not found or no matching containers running",
            "available_modules": available
        }
    
    return {
        "message": f"Module {app_name} collected successfully",
        "module": app_name,
        "count": len(matching_results),
        "results": matching_results,
    }

@app.get("/api/test-alert")
async def test_alert():
    """
    Send test alert to Discord (for configuration testing).
    
    This endpoint sends a test notification to verify Discord webhook configuration.
    Use this after setting up your webhook URL to ensure alerts will work properly.
    
    Returns:
        dict: Success status and message
    """
    from app.alerts import send_discord_webhook, format_service_alert
    
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    
    if not webhook_url:
        return {
            "success": False,
            "error": "DISCORD_WEBHOOK_URL not configured in .env file"
        }
    
    if webhook_url == "https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE":
        return {
            "success": False,
            "error": "DISCORD_WEBHOOK_URL still has placeholder value - update with real webhook"
        }
    
    # Create test alert embed
    test_embed = format_service_alert(
        service_name="test",
        prev_status="OK",
        new_status="OK",
        details={
            "message": "This is a test alert from HomeSentry",
            "response_ms": 42.0,
            "http_code": 200
        }
    )
    
    # Override title and description for test
    test_embed["title"] = "🧪 Test Alert - HomeSentry"
    test_embed["description"] = "If you can see this, Discord alerts are working correctly!"
    test_embed["fields"] = [
        {
            "name": "Status",
            "value": "✅ Configuration Valid",
            "inline": True
        },
        {
            "name": "Webhook",
            "value": "Connected Successfully",
            "inline": True
        }
    ]
    
    success = send_discord_webhook(webhook_url, test_embed)
    
    if success:
        logger.info("Test alert sent successfully")
        return {
            "success": True,
            "message": "Test alert sent successfully! Check your Discord channel."
        }
    else:
        return {
            "success": False,
            "error": "Failed to send test alert - check logs for details"
        }


@app.get("/api/debug/sleep-schedule")
async def debug_sleep_schedule():
    """
    Debug endpoint to verify sleep schedule configuration and current state.
    
    Returns current sleep schedule settings, whether we're in sleep hours,
    and tests some example times. Useful for troubleshooting alert suppression.
    
    Returns:
        dict: Sleep schedule configuration and current status
    """
    from app.alerts.sleep_schedule import get_sleep_schedule, is_in_sleep_hours
    from datetime import datetime
    
    # Get configuration
    start_time, end_time, enabled = get_sleep_schedule()
    
    # Check current time
    now = datetime.now()
    is_sleeping, reason = is_in_sleep_hours(now)
    
    # Get environment variables for verification
    env_vars = {
        "SLEEP_SCHEDULE_ENABLED": os.getenv("SLEEP_SCHEDULE_ENABLED", "(not set)"),
        "SLEEP_SCHEDULE_START": os.getenv("SLEEP_SCHEDULE_START", "(not set)"),
        "SLEEP_SCHEDULE_END": os.getenv("SLEEP_SCHEDULE_END", "(not set)"),
        "SLEEP_SUMMARY_ENABLED": os.getenv("SLEEP_SUMMARY_ENABLED", "(not set)"),
        "SLEEP_SUMMARY_TIME": os.getenv("SLEEP_SUMMARY_TIME", "(not set)"),
        "SLEEP_ALLOW_CRITICAL_ALERTS": os.getenv("SLEEP_ALLOW_CRITICAL_ALERTS", "(not set)"),
    }
    
    # Test a few specific times
    test_times = [
        datetime(2026, 1, 30, 3, 0),   # Middle of night
        datetime(2026, 1, 30, 7, 30),  # End of sleep
        datetime(2026, 1, 30, 8, 0),   # Morning
    ]
    
    test_results = []
    for test_time in test_times:
        is_test_sleeping, test_reason = is_in_sleep_hours(test_time)
        test_results.append({
            "time": test_time.strftime("%H:%M"),
            "is_sleeping": is_test_sleeping,
            "reason": test_reason
        })
    
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "environment_variables": env_vars,
        "parsed_config": {
            "enabled": enabled,
            "start_time": start_time.strftime("%H:%M") if start_time else None,
            "end_time": end_time.strftime("%H:%M") if end_time else None,
        },
        "current_status": {
            "is_in_sleep_hours": is_sleeping,
            "reason": reason,
            "alerts_suppressed": is_sleeping
        },
        "test_times": test_results
    }


if __name__ == "__main__":
    # This block allows running the app directly with: python -m app.main
    # Useful for development/debugging
    import uvicorn
    
    logger.info("Starting development server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info",
    )

