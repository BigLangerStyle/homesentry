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
from app.collectors import collect_all_system_metrics, check_all_services
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

