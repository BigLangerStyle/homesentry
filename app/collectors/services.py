"""
Service health check collector for HomeSentry.

This module monitors HTTP services via health checks, measuring response times,
tracking HTTP status codes, and detecting connection failures. Designed for
monitoring services like Plex, Jellyfin, Pi-hole, Home Assistant, and qBittorrent.
"""
import logging
import os
import json
import time
import asyncio
import requests
from urllib3.exceptions import InsecureRequestWarning

from app.storage import insert_service_status

logger = logging.getLogger(__name__)

# Suppress SSL warnings for self-signed certificates (common in home labs)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configuration from environment variables
SERVICE_CHECK_TIMEOUT = int(os.getenv("SERVICE_CHECK_TIMEOUT", "10"))
SERVICE_SLOW_THRESHOLD = float(os.getenv("SERVICE_SLOW_THRESHOLD", "3000"))  # milliseconds

# Service URLs from environment
SERVICES = {
    "plex": os.getenv("PLEX_URL", ""),
    "jellyfin": os.getenv("JELLYFIN_URL", ""),
    "pihole": os.getenv("PIHOLE_URL", ""),
    "homeassistant": os.getenv("HOMEASSISTANT_URL", ""),
    "qbittorrent": os.getenv("QBITTORRENT_URL", ""),
}

# Filter out empty URLs (unconfigured services)
ACTIVE_SERVICES = {name: url for name, url in SERVICES.items() if url}


def determine_service_status(
    http_code: int | None,
    response_ms: float | None,
    error: str | None,
    slow_threshold: float = SERVICE_SLOW_THRESHOLD
) -> str:
    """
    Determine service status based on HTTP response.
    
    Args:
        http_code: HTTP status code (None if connection failed)
        response_ms: Response time in milliseconds
        error: Error message if request failed
        slow_threshold: Threshold in milliseconds for slow response warning
    
    Returns:
        str: Status code - "OK", "WARN", or "FAIL"
    
    Status determination logic:
        - FAIL: Connection error, timeout, or HTTP 5xx
        - WARN: HTTP 3xx/4xx, or slow response (2xx but > threshold)
        - OK: HTTP 2xx with acceptable response time
    """
    # Connection error or timeout
    if error:
        return "FAIL"
    
    # No response code (shouldn't happen if no error, but defensive)
    if http_code is None:
        return "FAIL"
    
    # Server errors (500-599)
    if http_code >= 500:
        return "FAIL"
    
    # Success but slow response
    if 200 <= http_code < 300 and response_ms and response_ms > slow_threshold:
        return "WARN"
    
    # Client errors or redirects (300-499)
    if http_code >= 300:
        return "WARN"
    
    # Success (200-299) with acceptable response time
    return "OK"


def _sync_check_service(url: str, name: str, timeout: int = SERVICE_CHECK_TIMEOUT) -> dict:
    """
    Synchronous service health check (runs in thread pool).
    
    Performs an HTTP GET request to the service URL, measures response time,
    captures the HTTP status code, and handles various error conditions.
    
    Args:
        url: Service URL to check
        name: Service name for logging (e.g., "plex", "jellyfin")
        timeout: Request timeout in seconds
    
    Returns:
        dict: Check results containing:
            - name: Service name
            - url: Service URL checked
            - status: Determined status (OK/WARN/FAIL)
            - http_code: HTTP status code (None if failed)
            - response_ms: Response time in milliseconds (None if failed)
            - error: Error message (None if successful)
            - details_json: JSON string with detailed information
    """
    headers = {
        "User-Agent": "HomeSentry/0.1.0",
        "Accept": "*/*"
    }
    
    result = {
        "name": name,
        "url": url,
        "status": "FAIL",
        "http_code": None,
        "response_ms": None,
        "error": None,
        "details_json": None
    }
    
    try:
        # Measure request time
        start_time = time.time()
        response = requests.get(
            url,
            timeout=(3, timeout),  # (connect timeout, read timeout)
            verify=False,  # Accept self-signed certificates
            headers=headers,
            allow_redirects=True  # Follow redirects automatically
        )
        response_ms = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Store response details
        result["http_code"] = response.status_code
        result["response_ms"] = round(response_ms, 2)
        result["status"] = determine_service_status(
            response.status_code,
            response_ms,
            None,
            SERVICE_SLOW_THRESHOLD
        )
        
        # Build details JSON
        details = {
            "url": url,
            "http_code": response.status_code,
            "response_ms": result["response_ms"]
        }
        
        # Add warning if slow response
        if result["status"] == "WARN" and response_ms > SERVICE_SLOW_THRESHOLD:
            details["warning"] = "Slow response"
        
        result["details_json"] = json.dumps(details)
        
        logger.info(
            f"Service check [{name}]: {result['status']} "
            f"(HTTP {response.status_code}, {response_ms:.0f}ms)"
        )
        
    except requests.exceptions.Timeout:
        result["error"] = "Request timed out"
        result["details_json"] = json.dumps({
            "url": url,
            "error": "Timeout",
            "timeout": timeout
        })
        logger.warning(f"Service check [{name}]: Timeout after {timeout}s")
        
    except requests.exceptions.ConnectionError as e:
        result["error"] = "Connection failed"
        result["details_json"] = json.dumps({
            "url": url,
            "error": "ConnectionError",
            "message": str(e)
        })
        logger.warning(f"Service check [{name}]: Connection failed - {e}")
        
    except Exception as e:
        result["error"] = str(e)
        result["details_json"] = json.dumps({
            "url": url,
            "error": type(e).__name__,
            "message": str(e)
        })
        logger.error(f"Service check [{name}] failed: {e}")
    
    return result


async def check_service_health(
    url: str,
    name: str,
    timeout: int = SERVICE_CHECK_TIMEOUT
) -> dict:
    """
    Check service health asynchronously.
    
    Wraps the synchronous HTTP check in an async executor and writes
    results to the database.
    
    Args:
        url: Service URL to check
        name: Service name (e.g., 'plex', 'jellyfin')
        timeout: Request timeout in seconds
    
    Returns:
        dict: Check results from _sync_check_service
    """
    # Run synchronous check in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_check_service, url, name, timeout)
    
    # Write to database
    try:
        await insert_service_status(
            service=name,
            status=result["status"],
            response_ms=result.get("response_ms"),
            http_code=result.get("http_code"),
            details_json=result.get("details_json")
        )
    except Exception as e:
        logger.error(f"Failed to insert service status for {name}: {e}")
    
    return result


async def check_all_services() -> dict:
    """
    Check all configured services concurrently.
    
    Reads service URLs from ACTIVE_SERVICES (environment variables),
    checks each service concurrently using asyncio.gather, and returns
    results for all services.
    
    Returns:
        dict: Results keyed by service name, containing check results or errors
    
    Example:
        {
            "plex": {"status": "OK", "http_code": 200, "response_ms": 45.2, ...},
            "jellyfin": {"status": "FAIL", "error": "Connection failed", ...}
        }
    """
    results = {}
    
    if not ACTIVE_SERVICES:
        logger.warning("No services configured for monitoring")
        return results
    
    logger.info(f"Checking {len(ACTIVE_SERVICES)} services...")
    
    # Create tasks for concurrent checking
    tasks = [
        check_service_health(url, name)
        for name, url in ACTIVE_SERVICES.items()
    ]
    
    # Execute all checks concurrently
    check_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, (name, url) in enumerate(ACTIVE_SERVICES.items()):
        result = check_results[i]
        if isinstance(result, Exception):
            logger.error(f"Service check failed for {name}: {result}")
            results[name] = {"status": "FAIL", "error": str(result)}
        else:
            results[name] = result
    
    logger.info(f"Service checks completed: {len(results)} services checked")
    
    return results
