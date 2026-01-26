"""
HomeSentry - FastAPI application entry point

This module sets up the FastAPI application with basic endpoints,
logging configuration, and CORS middleware.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.storage import init_database
from app.collectors import collect_all_system_metrics, check_all_services

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


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    Logs startup information and configuration, and initializes the database.
    """
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
    
    logger.info("Application started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    Logs shutdown information.
    """
    logger.info("HomeSentry shutting down...")


@app.get("/")
async def root():
    """
    Root endpoint - returns welcome message and basic status.
    
    Returns:
        dict: Welcome message with version and status information
    """
    return {
        "message": "HomeSentry is running",
        "version": "0.1.0",
        "status": "healthy",
        "docs": "/docs",
        "health_check": "/healthz",
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

