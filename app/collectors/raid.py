"""
RAID Array Monitoring Collector for HomeSentry

Monitors mdadm software RAID arrays including:
- Array health status (clean, degraded, rebuilding, failed)
- Individual disk status within arrays
- Rebuild progress and ETA
- Active vs expected disk counts

Critical for preventing data loss in RAID configurations.
"""
import asyncio
import logging
import os
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.storage import insert_metric_sample
from app.alerts import process_alert

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration from Environment Variables
# ============================================================================
RAID_COLLECTION_ENABLED = os.getenv("RAID_COLLECTION_ENABLED", "true").lower() == "true"
RAID_ARRAYS = os.getenv("RAID_ARRAYS", "")  # Empty = auto-detect all arrays

# Path to mdstat file
MDSTAT_PATH = "/proc/mdstat"


# ============================================================================
# Regex Patterns for Parsing /proc/mdstat
# ============================================================================

# Array header line
# Example: "md0 : active raid5 sdd[2] sdc[1] sda[3]"
ARRAY_HEADER_REGEX = re.compile(r'^(md\d+)\s+:\s+(\w+)\s+(raid\d+)\s+(.+)$')

# Array status line with disk status indicators
# Example: "      7814037504 blocks super 1.2 level 5, 512k chunk, algorithm 2 [3/3] [UUU]"
ARRAY_STATUS_REGEX = re.compile(r'\[(\d+)/(\d+)\]\s+\[([U_]+)\]')

# Rebuild/recovery progress line
# Example: "      [===>.................]  recovery = 15.2% (1234567/7814037504) finish=123.4min speed=12345K/sec"
REBUILD_REGEX = re.compile(r'(recovery|resync)\s+=\s+([\d.]+)%.*?finish=([\d.]+)min\s+speed=(\d+)K/sec')


# ============================================================================
# Helper Functions
# ============================================================================

def parse_mdstat_file() -> str:
    """
    Read contents of /proc/mdstat file.
    
    Returns:
        str: Contents of /proc/mdstat, or empty string if file doesn't exist
    """
    if not os.path.exists(MDSTAT_PATH):
        logger.warning(f"{MDSTAT_PATH} not found - RAID monitoring disabled")
        return ""
    
    try:
        with open(MDSTAT_PATH, "r") as f:
            content = f.read()
        
        logger.debug(f"Read {len(content)} bytes from {MDSTAT_PATH}")
        return content
    
    except Exception as e:
        logger.error(f"Failed to read {MDSTAT_PATH}: {e}")
        return ""


def parse_member_disks(disk_string: str) -> List[Dict[str, Any]]:
    """
    Parse the disk list from array header.
    
    Example input: "sdd[2] sdc[1] sda[3]"
    
    Args:
        disk_string: Space-separated disk list with roles in brackets
    
    Returns:
        List of dicts with device name and role number
    """
    disks = []
    
    # Pattern: device_name[role_number]
    disk_pattern = re.compile(r'(\w+)\[(\d+)\]')
    
    for match in disk_pattern.finditer(disk_string):
        device = match.group(1)
        role = int(match.group(2))
        
        disks.append({
            "device": device,
            "role": role,
            "state": "active"  # Will be updated based on disk status indicators
        })
    
    return disks


def parse_array_block(lines: List[str]) -> Optional[Dict[str, Any]]:
    """
    Parse a single RAID array block from /proc/mdstat.
    
    An array block consists of:
    - Header line: "md0 : active raid5 sdd[2] sdc[1] sda[3]"
    - Status line: "      7814037504 blocks super 1.2 level 5, 512k chunk, algorithm 2 [3/3] [UUU]"
    - Optional rebuild line: "      [===>.................]  recovery = 15.2% ..."
    
    Args:
        lines: List of lines for this array (2-3 lines typically)
    
    Returns:
        Dict with parsed array information, or None if parsing fails
    """
    if not lines:
        return None
    
    # Parse header line
    header_match = ARRAY_HEADER_REGEX.match(lines[0])
    if not header_match:
        logger.warning(f"Failed to parse array header: {lines[0]}")
        return None
    
    array_name = header_match.group(1)
    array_state = header_match.group(2)  # active, degraded, etc.
    raid_level = header_match.group(3)   # raid5, raid1, etc.
    disk_string = header_match.group(4)  # "sdd[2] sdc[1] sda[3]"
    
    # Parse member disks
    member_disks = parse_member_disks(disk_string)
    
    # Parse status line (should be second line)
    status_match = None
    array_status = "unknown"
    disk_status = ""
    total_devices = 0
    active_devices = 0
    
    for line in lines[1:]:
        status_match = ARRAY_STATUS_REGEX.search(line)
        if status_match:
            total_devices = int(status_match.group(1))
            active_devices = int(status_match.group(2))
            disk_status = status_match.group(3)  # "UUU" or "_UU" etc.
            
            # Determine array status based on disk counts
            if active_devices == total_devices:
                array_status = "clean"
            else:
                array_status = "degraded"
            
            break
    
    if not status_match:
        logger.warning(f"Failed to parse status line for array {array_name}")
        # Continue anyway with partial data
    
    # Update member disk states based on disk_status indicators
    if disk_status and len(disk_status) == len(member_disks):
        for i, indicator in enumerate(disk_status):
            if indicator == 'U':
                member_disks[i]["state"] = "active"
            elif indicator == '_':
                member_disks[i]["state"] = "failed"
    
    # Check for rebuild/recovery progress
    rebuild_progress = None
    rebuild_speed = None
    rebuild_eta_minutes = None
    
    for line in lines[1:]:
        rebuild_match = REBUILD_REGEX.search(line)
        if rebuild_match:
            operation = rebuild_match.group(1)  # recovery or resync
            rebuild_progress = float(rebuild_match.group(2))
            rebuild_eta_minutes = float(rebuild_match.group(3))
            rebuild_speed = int(rebuild_match.group(4))  # KB/sec
            
            # If rebuilding, update array status
            array_status = "rebuilding" if operation == "recovery" else "resyncing"
            logger.info(f"Array {array_name} is {array_status}: {rebuild_progress}% complete")
            
            break
    
    # Count failed devices
    failed_devices = total_devices - active_devices
    spare_devices = 0  # TODO: Detect spare devices in future version
    
    return {
        "array_name": array_name,
        "raid_level": raid_level,
        "array_state": array_state,      # active, degraded, etc.
        "array_status": array_status,    # clean, degraded, rebuilding, resyncing
        "total_devices": total_devices,
        "active_devices": active_devices,
        "failed_devices": failed_devices,
        "spare_devices": spare_devices,
        "disk_status": disk_status,      # "UUU" or "_UU" etc.
        "member_disks": member_disks,
        "rebuild_progress": rebuild_progress,
        "rebuild_speed": rebuild_speed,
        "rebuild_eta_minutes": rebuild_eta_minutes,
    }


def parse_all_arrays(mdstat_content: str) -> List[Dict[str, Any]]:
    """
    Parse all RAID arrays from /proc/mdstat content.
    
    Args:
        mdstat_content: Contents of /proc/mdstat file
    
    Returns:
        List of parsed array dictionaries
    """
    if not mdstat_content:
        return []
    
    arrays = []
    lines = mdstat_content.strip().split('\n')
    
    # Skip header lines
    # Example header:
    # Personalities : [raid5] [linear] [multipath] [raid0] [raid1] [raid6] [raid4] [raid10]
    # unused devices: <none>
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip header lines and empty lines
        if line.startswith('Personalities') or line.startswith('unused') or not line.strip():
            i += 1
            continue
        
        # Check if this is an array header line
        if ARRAY_HEADER_REGEX.match(line):
            # Collect lines for this array (header + status + optional rebuild)
            array_lines = [line]
            i += 1
            
            # Collect following indented lines (status and rebuild info)
            while i < len(lines) and (lines[i].startswith('      ') or lines[i].startswith('\t')):
                array_lines.append(lines[i])
                i += 1
            
            # Parse this array block
            array_data = parse_array_block(array_lines)
            if array_data:
                arrays.append(array_data)
                logger.debug(f"Parsed array: {array_data['array_name']} ({array_data['raid_level']})")
        else:
            i += 1
    
    return arrays


def filter_configured_arrays(arrays: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter arrays based on RAID_ARRAYS configuration.
    
    If RAID_ARRAYS is empty, return all arrays (auto-detect).
    If RAID_ARRAYS is set, only return arrays in the list.
    
    Args:
        arrays: List of all detected arrays
    
    Returns:
        List of arrays to monitor
    """
    if not RAID_ARRAYS:
        logger.debug(f"Auto-detect mode: monitoring all {len(arrays)} arrays")
        return arrays
    
    # Parse configured array names
    configured = [name.strip() for name in RAID_ARRAYS.split(',') if name.strip()]
    
    # Filter arrays
    filtered = [arr for arr in arrays if arr['array_name'] in configured]
    
    logger.debug(f"Monitoring {len(filtered)}/{len(arrays)} arrays: {configured}")
    return filtered


async def store_raid_metrics(array: Dict[str, Any]) -> None:
    """
    Store RAID array metrics in the database.
    
    Args:
        array: Parsed array dictionary with all metrics
    """
    array_name = array['array_name']
    
    # Determine overall status
    if array['array_status'] == 'clean' and array['array_state'] == 'active':
        overall_status = 'OK'
    elif array['array_status'] in ['rebuilding', 'resyncing']:
        overall_status = 'WARN'
    else:
        overall_status = 'FAIL'
    
    # Store array health metric
    await insert_metric_sample(
        category="raid",
        name=f"array_{array_name}_health",
        value_num=1 if overall_status == 'OK' else 0,
        status=overall_status,
        details_json=json.dumps({
            "array_name": array_name,
            "raid_level": array['raid_level'],
            "array_state": array['array_state'],
            "array_status": array['array_status'],
            "disk_status": array['disk_status']
        })
    )
    
    # Store active disk count (critical metric!)
    disk_status = 'OK' if array['active_devices'] == array['total_devices'] else 'FAIL'
    await insert_metric_sample(
        category="raid",
        name=f"array_{array_name}_active_disks",
        value_num=array['active_devices'],
        status=disk_status,
        details_json=json.dumps({
            "array_name": array_name,
            "total_devices": array['total_devices'],
            "failed_devices": array['failed_devices'],
            "disk_status": array['disk_status']
        })
    )
    
    # Store rebuild progress if rebuilding
    if array['rebuild_progress'] is not None:
        await insert_metric_sample(
            category="raid",
            name=f"array_{array_name}_rebuild_progress",
            value_num=array['rebuild_progress'],
            status='WARN',  # Rebuilding is a warning state
            details_json=json.dumps({
                "array_name": array_name,
                "rebuild_speed": array['rebuild_speed'],
                "rebuild_eta_minutes": array['rebuild_eta_minutes']
            })
        )


async def generate_raid_alerts(array: Dict[str, Any]) -> None:
    """
    Generate alerts for RAID array status changes.
    
    Args:
        array: Parsed array dictionary with all metrics
    """
    array_name = array['array_name']
    
    # Critical alert: Array degraded
    if array['array_status'] == 'degraded' or array['active_devices'] < array['total_devices']:
        await process_alert(
            category='raid',
            name=f"{array_name}_degraded",
            new_status='FAIL',
            details={
                'message': f"🚨 CRITICAL: RAID array {array_name} is DEGRADED! {array['active_devices']}/{array['total_devices']} disks active. {array['disk_status']}",
                'array_name': array_name,
                'raid_level': array['raid_level'],
                'active_devices': array['active_devices'],
                'total_devices': array['total_devices'],
                'failed_devices': array['failed_devices'],
                'disk_status': array['disk_status'],
                'member_disks': array['member_disks']
            }
        )
    
    # Warning alert: Array rebuilding
    elif array['array_status'] in ['rebuilding', 'resyncing']:
        rebuild_msg = f"⚠️ RAID array {array_name} rebuilding: {array['rebuild_progress']:.1f}% complete"
        if array['rebuild_eta_minutes']:
            rebuild_msg += f" (ETA: {array['rebuild_eta_minutes']:.0f} min)"
        
        await process_alert(
            category='raid',
            name=f"{array_name}_rebuilding",
            new_status='WARN',
            details={
                'message': rebuild_msg,
                'array_name': array_name,
                'rebuild_progress': array['rebuild_progress'],
                'rebuild_speed': array['rebuild_speed'],
                'rebuild_eta_minutes': array['rebuild_eta_minutes']
            }
        )
    
    # Success alert: Array restored (clean and all disks active)
    elif array['array_status'] == 'clean' and array['active_devices'] == array['total_devices']:
        await process_alert(
            category='raid',
            name=f"{array_name}_health",
            new_status='OK',
            details={
                'message': f"✅ RAID array {array_name} is healthy. All {array['total_devices']} disks active. {array['disk_status']}",
                'array_name': array_name,
                'raid_level': array['raid_level'],
                'disk_status': array['disk_status']
            }
        )


# ============================================================================
# Main Collection Function
# ============================================================================

async def collect_all_raid_metrics() -> Dict[str, Any]:
    """
    Collect RAID metrics for all configured arrays.
    
    This is the main entry point for RAID monitoring. It:
    1. Reads /proc/mdstat
    2. Parses all RAID arrays
    3. Filters to configured arrays (or all if auto-detect)
    4. Stores metrics in database
    5. Generates alerts for status changes
    
    Returns:
        Dict mapping array names to their metrics
    
    Raises:
        Exception: May raise exceptions which should be caught by caller
    """
    if not RAID_COLLECTION_ENABLED:
        logger.debug("RAID collection is disabled in configuration")
        return {}
    
    # Read /proc/mdstat
    mdstat_content = parse_mdstat_file()
    if not mdstat_content:
        logger.info("No RAID arrays detected or /proc/mdstat not available")
        return {}
    
    # Parse all arrays
    all_arrays = parse_all_arrays(mdstat_content)
    if not all_arrays:
        logger.info("No RAID arrays found in /proc/mdstat")
        return {}
    
    logger.info(f"Detected {len(all_arrays)} RAID array(s)")
    
    # Filter to configured arrays
    arrays = filter_configured_arrays(all_arrays)
    if not arrays:
        logger.warning(f"No arrays match configured list: {RAID_ARRAYS}")
        return {}
    
    # Process each array
    results = {}
    for array in arrays:
        array_name = array['array_name']
        
        try:
            # Store metrics
            await store_raid_metrics(array)
            
            # Generate alerts
            await generate_raid_alerts(array)
            
            # Build result dictionary
            results[array_name] = {
                'raid_level': array['raid_level'],
                'array_state': array['array_state'],
                'array_status': array['array_status'],
                'total_devices': array['total_devices'],
                'active_devices': array['active_devices'],
                'failed_devices': array['failed_devices'],
                'disk_status': array['disk_status'],
                'member_disks': array['member_disks'],
                'status': 'OK' if array['array_status'] == 'clean' and array['active_devices'] == array['total_devices'] else ('WARN' if array['array_status'] in ['rebuilding', 'resyncing'] else 'FAIL')
            }
            
            # Add rebuild info if present
            if array['rebuild_progress'] is not None:
                results[array_name]['rebuild_progress'] = array['rebuild_progress']
                results[array_name]['rebuild_eta_minutes'] = array['rebuild_eta_minutes']
                results[array_name]['rebuild_speed_kbps'] = array['rebuild_speed']
            
            logger.info(
                f"RAID array {array_name}: {array['raid_level']}, "
                f"{array['active_devices']}/{array['total_devices']} disks, "
                f"status={array['array_status']}"
            )
        
        except Exception as e:
            logger.error(f"Failed to process array {array_name}: {e}", exc_info=True)
            results[array_name] = {
                'error': str(e),
                'status': 'FAIL'
            }
    
    return results
