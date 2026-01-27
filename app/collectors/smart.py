"""
SMART Drive Health Monitoring Collector for HomeSentry

Monitors drive health using smartctl from smartmontools package.
Tracks critical indicators of drive failure including:
- Overall SMART health status (PASSED/FAILED)
- Drive temperature (with configurable thresholds)
- Reallocated sectors (bad sectors that have been remapped)
- Pending sectors (sectors waiting to be reallocated)
- Uncorrectable sectors (sectors that couldn't be read or written)
- Power-on hours (drive age tracking)

This collector provides early warning signs of drive failures, allowing
proactive replacement before data loss occurs.
"""
import asyncio
import logging
import os
import json
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.storage import insert_metric_sample
from app.alerts import process_alert

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration from Environment Variables
# ============================================================================
SMART_COLLECTION_ENABLED = os.getenv("SMART_COLLECTION_ENABLED", "true").lower() == "true"
SMART_DEVICES = os.getenv("SMART_DEVICES", "/dev/sda,/dev/sdb,/dev/sdc,/dev/sdd")

# Temperature thresholds (Celsius)
# HDDs: Normal = 20-40°C, Warning = 50°C+, Critical = 60°C+
# SSDs: Normal = 20-50°C, Warning = 60°C+, Critical = 70°C+
SMART_TEMP_WARN_THRESHOLD = float(os.getenv("SMART_TEMP_WARN_THRESHOLD", "50"))
SMART_TEMP_FAIL_THRESHOLD = float(os.getenv("SMART_TEMP_FAIL_THRESHOLD", "60"))

# SMART attribute IDs (standard across most drives)
ATTR_REALLOCATED_SECTORS = 5
ATTR_PENDING_SECTORS = 197
ATTR_UNCORRECTABLE_SECTORS = 198
ATTR_TEMPERATURE = 194
ATTR_POWER_ON_HOURS = 9


# ============================================================================
# Helper Functions
# ============================================================================

def parse_device_list() -> List[str]:
    """
    Parse comma-separated device list from environment variable.
    
    Returns:
        List[str]: List of device paths (e.g., ["/dev/sda", "/dev/sdb"])
    """
    if not SMART_DEVICES:
        return []
    
    # Split by comma and strip whitespace
    devices = [d.strip() for d in SMART_DEVICES.split(",") if d.strip()]
    
    logger.debug(f"Configured SMART devices: {devices}")
    return devices


def check_smartctl_available() -> bool:
    """
    Check if smartctl is available on the system.
    
    Returns:
        bool: True if smartctl command is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["which", "smartctl"],
            capture_output=True,
            text=True,
            timeout=5
        )
        available = result.returncode == 0
        
        if available:
            logger.debug(f"smartctl found at: {result.stdout.strip()}")
        else:
            logger.warning("smartctl not found - SMART monitoring will be disabled")
        
        return available
    
    except Exception as e:
        logger.error(f"Error checking for smartctl: {e}")
        return False


def determine_temperature_status(temperature: float) -> str:
    """
    Determine status based on drive temperature.
    
    Args:
        temperature: Temperature in Celsius
    
    Returns:
        str: Status - "OK", "WARN", or "FAIL"
    """
    if temperature >= SMART_TEMP_FAIL_THRESHOLD:
        return "FAIL"
    elif temperature >= SMART_TEMP_WARN_THRESHOLD:
        return "WARN"
    return "OK"


# ============================================================================
# Synchronous Collection Functions (run in thread pool)
# ============================================================================

def _sync_get_smart_health(device: str) -> Optional[str]:
    """
    Get SMART health status for a drive (synchronous).
    
    Args:
        device: Device path (e.g., "/dev/sda")
    
    Returns:
        str: Health status ("PASSED" or "FAILED"), or None if unavailable
    """
    try:
        result = subprocess.run(
            ["smartctl", "-H", "-j", device],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Parse JSON output
        data = json.loads(result.stdout)
        
        # Extract health status
        smart_status = data.get("smart_status", {})
        passed = smart_status.get("passed", False)
        
        return "PASSED" if passed else "FAILED"
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout reading SMART health from {device}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON output from smartctl for {device}")
        return None
    except Exception as e:
        logger.error(f"Error reading SMART health from {device}: {e}")
        return None


def _sync_get_smart_attributes(device: str) -> Optional[Dict[str, Any]]:
    """
    Get SMART attributes for a drive (synchronous).
    
    Args:
        device: Device path (e.g., "/dev/sda")
    
    Returns:
        Dict with parsed SMART data, or None if unavailable
        Example: {
            "device": "/dev/sda",
            "model": "WDC WD40EFRX-68N32N0",
            "serial": "WD-WX32D954AZLA",
            "temperature": 24,
            "power_on_hours": 17,
            "reallocated_sectors": 0,
            "pending_sectors": 0,
            "uncorrectable_sectors": 0
        }
    """
    try:
        # Get both device info and SMART attributes in one call
        result = subprocess.run(
            ["smartctl", "-i", "-A", "-j", device],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Parse JSON output
        data = json.loads(result.stdout)
        
        # Extract device information
        model_name = data.get("model_name", "Unknown")
        serial_number = data.get("serial_number", "Unknown")
        
        # Extract temperature
        temperature = None
        temp_data = data.get("temperature", {})
        if "current" in temp_data:
            temperature = temp_data["current"]
        
        # Extract SMART attributes
        attributes = {}
        attr_table = data.get("ata_smart_attributes", {}).get("table", [])
        
        for attr in attr_table:
            attr_id = attr.get("id")
            if attr_id in [
                ATTR_REALLOCATED_SECTORS,
                ATTR_PENDING_SECTORS,
                ATTR_UNCORRECTABLE_SECTORS,
                ATTR_TEMPERATURE,
                ATTR_POWER_ON_HOURS
            ]:
                raw_value = attr.get("raw", {}).get("value", 0)
                attributes[attr_id] = raw_value
        
        # If temperature wasn't in temperature field, try attribute
        if temperature is None and ATTR_TEMPERATURE in attributes:
            temperature = attributes[ATTR_TEMPERATURE]
        
        return {
            "device": device,
            "model": model_name,
            "serial": serial_number,
            "temperature": temperature,
            "power_on_hours": attributes.get(ATTR_POWER_ON_HOURS, 0),
            "reallocated_sectors": attributes.get(ATTR_REALLOCATED_SECTORS, 0),
            "pending_sectors": attributes.get(ATTR_PENDING_SECTORS, 0),
            "uncorrectable_sectors": attributes.get(ATTR_UNCORRECTABLE_SECTORS, 0)
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout reading SMART attributes from {device}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON output from smartctl for {device}")
        return None
    except Exception as e:
        logger.error(f"Error reading SMART attributes from {device}: {e}")
        return None


def _sync_collect_drive_smart_data(device: str) -> Optional[Dict[str, Any]]:
    """
    Collect complete SMART data for a single drive (synchronous).
    
    Args:
        device: Device path (e.g., "/dev/sda")
    
    Returns:
        Dict with complete SMART data, or None if collection fails
    """
    try:
        logger.debug(f"Collecting SMART data for {device}...")
        
        # Get health status
        health_status = _sync_get_smart_health(device)
        if health_status is None:
            logger.warning(f"Could not read SMART health from {device}")
            return None
        
        # Get attributes
        attributes = _sync_get_smart_attributes(device)
        if attributes is None:
            logger.warning(f"Could not read SMART attributes from {device}")
            return None
        
        # Combine data
        smart_data = {
            "device": device,
            "model": attributes["model"],
            "serial": attributes["serial"],
            "smart_health": health_status,
            "temperature": attributes["temperature"],
            "power_on_hours": attributes["power_on_hours"],
            "reallocated_sectors": attributes["reallocated_sectors"],
            "pending_sectors": attributes["pending_sectors"],
            "uncorrectable_sectors": attributes["uncorrectable_sectors"]
        }
        
        logger.debug(
            f"SMART data for {device}: health={health_status}, "
            f"temp={attributes['temperature']}°C, "
            f"reallocated={attributes['reallocated_sectors']}"
        )
        
        return smart_data
    
    except Exception as e:
        logger.error(f"Failed to collect SMART data for {device}: {e}")
        return None


# ============================================================================
# Async Collection Functions
# ============================================================================

async def collect_drive_smart_metrics(device: str) -> Optional[Dict[str, Any]]:
    """
    Collect SMART metrics for a single drive.
    
    This runs the synchronous collection in a thread pool to avoid blocking.
    
    Args:
        device: Device path (e.g., "/dev/sda")
    
    Returns:
        Dict with SMART data, or None if collection fails
    """
    loop = asyncio.get_event_loop()
    smart_data = await loop.run_in_executor(None, _sync_collect_drive_smart_data, device)
    
    if smart_data is None:
        return None
    
    # Store metrics in database
    await store_smart_health_metric(smart_data)
    
    if smart_data["temperature"] is not None:
        await store_temperature_metric(smart_data)
    
    await store_reallocated_sectors_metric(smart_data)
    await store_pending_sectors_metric(smart_data)
    await store_power_on_hours_metric(smart_data)
    
    # Process alerts
    await process_smart_alerts(smart_data)
    
    return smart_data


async def store_smart_health_metric(smart_data: Dict[str, Any]) -> None:
    """
    Store SMART health status metric in database.
    
    Args:
        smart_data: SMART data dict with health information
    """
    try:
        device = smart_data["device"]
        health = smart_data["smart_health"]
        
        # Determine status
        status = "OK" if health == "PASSED" else "FAIL"
        
        # Value: 1 for PASSED, 0 for FAILED
        value = 1 if health == "PASSED" else 0
        
        details = {
            "device": device,
            "model": smart_data["model"],
            "serial": smart_data["serial"],
            "smart_health": health
        }
        
        await insert_metric_sample(
            category="smart",
            name=f"drive_{device.replace('/', '_')}_health",
            value_num=value,
            status=status,
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store SMART health metric: {e}")


async def store_temperature_metric(smart_data: Dict[str, Any]) -> None:
    """
    Store drive temperature metric in database.
    
    Args:
        smart_data: SMART data dict with temperature information
    """
    try:
        device = smart_data["device"]
        temperature = smart_data["temperature"]
        
        if temperature is None:
            return
        
        # Determine status based on temperature
        status = determine_temperature_status(temperature)
        
        details = {
            "device": device,
            "model": smart_data["model"]
        }
        
        await insert_metric_sample(
            category="smart",
            name=f"drive_{device.replace('/', '_')}_temperature",
            value_num=temperature,
            status=status,
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store temperature metric: {e}")


async def store_reallocated_sectors_metric(smart_data: Dict[str, Any]) -> None:
    """
    Store reallocated sectors metric in database.
    
    Args:
        smart_data: SMART data dict with reallocated sectors count
    """
    try:
        device = smart_data["device"]
        reallocated = smart_data["reallocated_sectors"]
        
        # ANY reallocated sectors is a warning sign
        status = "OK" if reallocated == 0 else "WARN"
        
        details = {
            "device": device,
            "model": smart_data["model"]
        }
        
        await insert_metric_sample(
            category="smart",
            name=f"drive_{device.replace('/', '_')}_reallocated_sectors",
            value_num=reallocated,
            status=status,
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store reallocated sectors metric: {e}")


async def store_pending_sectors_metric(smart_data: Dict[str, Any]) -> None:
    """
    Store pending sectors metric in database.
    
    Args:
        smart_data: SMART data dict with pending sectors count
    """
    try:
        device = smart_data["device"]
        pending = smart_data["pending_sectors"]
        
        # Pending sectors indicate problems
        status = "OK" if pending == 0 else "WARN"
        
        details = {
            "device": device,
            "model": smart_data["model"]
        }
        
        await insert_metric_sample(
            category="smart",
            name=f"drive_{device.replace('/', '_')}_pending_sectors",
            value_num=pending,
            status=status,
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store pending sectors metric: {e}")


async def store_power_on_hours_metric(smart_data: Dict[str, Any]) -> None:
    """
    Store power-on hours metric in database.
    
    This is informational only - no status thresholds.
    
    Args:
        smart_data: SMART data dict with power-on hours
    """
    try:
        device = smart_data["device"]
        hours = smart_data["power_on_hours"]
        
        details = {
            "device": device,
            "model": smart_data["model"]
        }
        
        await insert_metric_sample(
            category="smart",
            name=f"drive_{device.replace('/', '_')}_power_on_hours",
            value_num=hours,
            status="OK",
            details_json=json.dumps(details)
        )
    
    except Exception as e:
        logger.error(f"Failed to store power-on hours metric: {e}")


async def process_smart_alerts(smart_data: Dict[str, Any]) -> None:
    """
    Process alerts for SMART status changes.
    
    Generates alerts for:
    - SMART health failures (immediate FAIL alert)
    - Reallocated sectors > 0 (warning)
    - Pending sectors > 0 (warning)
    - Temperature thresholds exceeded (warn/fail)
    
    Args:
        smart_data: SMART data dict
    """
    device = smart_data["device"]
    device_clean = device.replace('/', '_')
    
    try:
        # Alert on SMART health failure
        health_status = "OK" if smart_data["smart_health"] == "PASSED" else "FAIL"
        await process_alert(
            category="smart",
            name=f"{device_clean}_health",
            new_status=health_status,
            details={
                "device": device,
                "model": smart_data["model"],
                "serial": smart_data["serial"],
                "smart_health": smart_data["smart_health"]
            }
        )
        
        # Alert on temperature
        if smart_data["temperature"] is not None:
            temp_status = determine_temperature_status(smart_data["temperature"])
            await process_alert(
                category="smart",
                name=f"{device_clean}_temperature",
                new_status=temp_status,
                details={
                    "device": device,
                    "model": smart_data["model"],
                    "temperature": smart_data["temperature"]
                }
            )
        
        # Alert on reallocated sectors
        reallocated_status = "OK" if smart_data["reallocated_sectors"] == 0 else "WARN"
        await process_alert(
            category="smart",
            name=f"{device_clean}_reallocated",
            new_status=reallocated_status,
            details={
                "device": device,
                "model": smart_data["model"],
                "reallocated_sectors": smart_data["reallocated_sectors"]
            }
        )
        
        # Alert on pending sectors
        pending_status = "OK" if smart_data["pending_sectors"] == 0 else "WARN"
        await process_alert(
            category="smart",
            name=f"{device_clean}_pending",
            new_status=pending_status,
            details={
                "device": device,
                "model": smart_data["model"],
                "pending_sectors": smart_data["pending_sectors"]
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to process alerts for {device}: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

async def collect_all_smart_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Collect SMART metrics for all configured drives.
    
    This is the main entry point for SMART monitoring. It collects health
    status, temperature, and critical attributes for all drives, stores them
    in the database, and processes alerts.
    
    Returns:
        Dict with SMART data keyed by device path
        Example: {
            "/dev/sda": {"smart_health": "PASSED", "temperature": 24, ...},
            "/dev/sdb": {"smart_health": "PASSED", "temperature": 35, ...}
        }
    """
    if not SMART_COLLECTION_ENABLED:
        logger.debug("SMART collection is disabled in configuration")
        return {}
    
    # Check if smartctl is available
    if not check_smartctl_available():
        logger.warning("smartctl not available - SMART monitoring disabled")
        return {}
    
    # Get list of devices to monitor
    devices = parse_device_list()
    
    if not devices:
        logger.warning("No SMART devices configured - skipping SMART collection")
        return {}
    
    logger.info(f"Collecting SMART metrics for {len(devices)} drives...")
    
    # Collect data for all drives concurrently
    tasks = [collect_drive_smart_metrics(device) for device in devices]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Build results dict
    results = {}
    for device, smart_data in zip(devices, results_list):
        if isinstance(smart_data, Exception):
            logger.error(f"SMART collection failed for {device}: {smart_data}")
            continue
        
        if smart_data is None:
            logger.warning(f"No SMART data available for {device}")
            continue
        
        results[device] = smart_data
        
        # Log summary
        logger.info(
            f"Drive [{device}]: {smart_data['smart_health']} "
            f"(temp: {smart_data['temperature']}°C, "
            f"reallocated: {smart_data['reallocated_sectors']}, "
            f"pending: {smart_data['pending_sectors']})"
        )
    
    logger.info(f"SMART metrics collection complete: {len(results)} drives monitored")
    
    return results
