"""
System metrics collector for HomeSentry

Monitors CPU, RAM, and disk usage with threshold-based status determination.
Automatically writes metrics to the database for tracking and alerting.
"""
import logging
import os
import json
from datetime import datetime
import psutil
from app.storage import insert_metric_sample

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration - Thresholds from Environment Variables
# ============================================================================
CPU_WARN_THRESHOLD = float(os.getenv("CPU_WARN_THRESHOLD", "80"))
CPU_FAIL_THRESHOLD = float(os.getenv("CPU_FAIL_THRESHOLD", "95"))

MEMORY_WARN_THRESHOLD = float(os.getenv("MEMORY_WARN_THRESHOLD", "85"))
MEMORY_FAIL_THRESHOLD = float(os.getenv("MEMORY_FAIL_THRESHOLD", "95"))

DISK_WARN_PERCENT = float(os.getenv("DISK_WARN_PERCENT", "85"))
DISK_FAIL_PERCENT = float(os.getenv("DISK_FAIL_PERCENT", "95"))
DISK_WARN_GB = float(os.getenv("DISK_WARN_GB", "50"))
DISK_FAIL_GB = float(os.getenv("DISK_FAIL_GB", "10"))

# Real filesystem types (exclude virtual/temporary filesystems)
REAL_FSTYPES = {
    "ext4",
    "ext3",
    "ext2",
    "xfs",
    "btrfs",
    "zfs",
    "ntfs",
    "vfat",
    "exfat",
    "fuseblk",
}


# ============================================================================
# Status Determination Functions
# ============================================================================
def determine_cpu_status(cpu_percent: float) -> str:
    """
    Determine CPU status based on usage percentage.

    Args:
        cpu_percent: CPU usage percentage (0-100)

    Returns:
        Status string: "OK", "WARN", or "FAIL"
    """
    if cpu_percent > CPU_FAIL_THRESHOLD:
        return "FAIL"
    elif cpu_percent > CPU_WARN_THRESHOLD:
        return "WARN"
    return "OK"


def determine_memory_status(memory_percent: float) -> str:
    """
    Determine memory status based on usage percentage.

    Args:
        memory_percent: Memory usage percentage (0-100)

    Returns:
        Status string: "OK", "WARN", or "FAIL"
    """
    if memory_percent > MEMORY_FAIL_THRESHOLD:
        return "FAIL"
    elif memory_percent > MEMORY_WARN_THRESHOLD:
        return "WARN"
    return "OK"


def determine_disk_status(free_gb: float, percent_used: float) -> str:
    """
    Determine disk status based on free space and usage percentage.

    Uses dual thresholds: alerts if EITHER free space is low OR usage is high.
    This catches both large disks with little free space and small disks that are full.

    Args:
        free_gb: Free space in gigabytes
        percent_used: Disk usage percentage (0-100)

    Returns:
        Status string: "OK", "WARN", or "FAIL"
    """
    # Critical: < 5% free OR < 10GB free
    if percent_used > DISK_FAIL_PERCENT or free_gb < DISK_FAIL_GB:
        return "FAIL"
    # Warning: < 15% free OR < 50GB free
    elif percent_used > DISK_WARN_PERCENT or free_gb < DISK_WARN_GB:
        return "WARN"
    return "OK"


def is_real_disk(partition) -> bool:
    """
    Check if partition is a real disk (not virtual/temporary filesystem).

    Filters out:
    - Virtual filesystems (tmpfs, devtmpfs, squashfs, overlay, etc.)
    - Docker bind mounts (individual files like /etc/resolv.conf)
    - Very small partitions (< 1GB, typically EFI/boot partitions)
    - /host/* paths when direct mounts exist (prefer /mnt/Array over /host/mnt/Array)

    Args:
        partition: psutil.disk_partitions() partition object

    Returns:
        True if partition should be monitored, False otherwise
    """
    # Filter 1: Must be a real filesystem type
    if partition.fstype not in REAL_FSTYPES:
        return False
    
    # Filter 2: Skip Docker bind mounts (files, not directories)
    # These show up as individual files like /etc/resolv.conf, /etc/hostname
    if partition.mountpoint.startswith("/etc/") and partition.mountpoint.count("/") > 1:
        return False
    
    # Filter 3: Skip very small partitions (< 1GB total)
    # This excludes EFI boot partitions, recovery partitions, etc.
    try:
        usage = psutil.disk_usage(partition.mountpoint)
        total_gb = usage.total / (1024**3)
        if total_gb < 1.0:
            return False
    except (PermissionError, OSError):
        # If we can't access it, skip it
        return False
    
    # Filter 4: Skip /host/* paths if we have a direct mount
    # Prefer /mnt/Array over /host/mnt/Array to avoid duplicates
    if partition.mountpoint.startswith("/host/"):
        # Extract the real path (e.g., /host/mnt/Array -> /mnt/Array)
        real_path = partition.mountpoint.replace("/host", "", 1)
        # Check if this same path exists as a direct mount
        all_mounts = [p.mountpoint for p in psutil.disk_partitions()]
        if real_path in all_mounts and real_path != "/":
            return False
    
    return True


# ============================================================================
# Metric Collection Functions
# ============================================================================
async def collect_cpu_metrics() -> dict | None:
    """
    Collect CPU metrics and write to database.

    Collects:
    - Overall CPU usage percentage
    - Per-core CPU usage percentages
    - Load averages (1, 5, 15 minute)

    Returns:
        Dict with CPU metrics and status, or None on failure
        Example: {
            "cpu_percent": 45.2,
            "load_avg": (1.5, 1.2, 1.1),
            "per_core": [45.2, 38.1, 52.3, 41.0],
            "status": "OK"
        }
    """
    try:
        # Collect CPU data (interval=1 ensures accurate reading)
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        load_avg = psutil.getloadavg()

        # Determine status based on overall CPU usage
        status = determine_cpu_status(cpu_percent)

        # Build details JSON with additional context
        details = json.dumps(
            {
                "per_core": cpu_per_core,
                "load_avg_1m": load_avg[0],
                "load_avg_5m": load_avg[1],
                "load_avg_15m": load_avg[2],
            }
        )

        # Insert main CPU percentage metric
        await insert_metric_sample(
            category="system",
            name="cpu_percent",
            value_num=cpu_percent,
            status=status,
            details_json=details,
        )

        # Also insert load averages as separate metrics
        await insert_metric_sample(
            category="system", name="cpu_load_1m", value_num=load_avg[0], status="OK"
        )

        await insert_metric_sample(
            category="system", name="cpu_load_5m", value_num=load_avg[1], status="OK"
        )

        await insert_metric_sample(
            category="system", name="cpu_load_15m", value_num=load_avg[2], status="OK"
        )

        logger.info(f"Collected CPU metrics: {cpu_percent:.1f}% ({status})")

        return {
            "cpu_percent": cpu_percent,
            "load_avg": load_avg,
            "per_core": cpu_per_core,
            "status": status,
        }

    except Exception as e:
        logger.error(f"Failed to collect CPU metrics: {e}")
        return None


async def collect_memory_metrics() -> dict | None:
    """
    Collect memory metrics and write to database.

    Collects:
    - Total RAM (GB)
    - Used RAM (GB and percentage)
    - Available RAM (GB)
    - Swap usage (if available)

    Returns:
        Dict with memory metrics and status, or None on failure
        Example: {
            "total_gb": 8.0,
            "used_gb": 5.2,
            "available_gb": 2.8,
            "percent": 65.0,
            "swap_used_gb": 0.5,
            "status": "OK"
        }
    """
    try:
        # Collect memory data
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Convert bytes to GB
        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        available_gb = mem.available / (1024**3)
        swap_total_gb = swap.total / (1024**3)
        swap_used_gb = swap.used / (1024**3)

        # Determine status based on memory usage percentage
        status = determine_memory_status(mem.percent)

        # Build details JSON
        details = json.dumps(
            {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "available_gb": round(available_gb, 2),
                "swap_total_gb": round(swap_total_gb, 2),
                "swap_used_gb": round(swap_used_gb, 2),
                "swap_percent": swap.percent,
            }
        )

        # Insert memory percentage metric
        await insert_metric_sample(
            category="system",
            name="memory_percent",
            value_num=mem.percent,
            status=status,
            details_json=details,
        )

        # Insert memory used in GB
        await insert_metric_sample(
            category="system",
            name="memory_used_gb",
            value_num=used_gb,
            status=status,
        )

        # Insert total memory
        await insert_metric_sample(
            category="system",
            name="memory_total_gb",
            value_num=total_gb,
            status="OK",
        )

        logger.info(
            f"Collected memory metrics: {mem.percent:.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB) ({status})"
        )

        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "available_gb": round(available_gb, 2),
            "percent": mem.percent,
            "swap_used_gb": round(swap_used_gb, 2),
            "swap_percent": swap.percent,
            "status": status,
        }

    except Exception as e:
        logger.error(f"Failed to collect memory metrics: {e}")
        return None


async def collect_disk_metrics() -> dict | None:
    """
    Collect disk metrics for all real filesystems and write to database.

    Discovers all mounted filesystems and filters out virtual ones (tmpfs, devtmpfs, etc.).
    For each real disk, collects total size, used space, free space, and usage percentage.

    Returns:
        Dict with disk metrics per mountpoint, or None on failure
        Example: {
            "/": {"total_gb": 110.5, "free_gb": 45.2, "percent_used": 59.1, "status": "OK"},
            "/mnt/Array": {"total_gb": 7300.0, "free_gb": 2500.0, "percent_used": 65.8, "status": "OK"}
        }
    """
    try:
        partitions = psutil.disk_partitions()
        disk_results = {}

        for partition in partitions:
            # Skip virtual filesystems and unwanted mounts
            if not is_real_disk(partition):
                # Use debug level for most, info for interesting skips
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    total_gb = usage.total / (1024**3)
                    # Log small partitions at info level to show filtering is working
                    if total_gb < 1.0 and partition.fstype in REAL_FSTYPES:
                        logger.info(
                            f"Skipping small partition: {partition.mountpoint} ({total_gb:.2f}GB, {partition.fstype})"
                        )
                    else:
                        logger.debug(
                            f"Skipping: {partition.mountpoint} ({partition.fstype})"
                        )
                except:
                    logger.debug(
                        f"Skipping inaccessible: {partition.mountpoint} ({partition.fstype})"
                    )
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)

                # Convert to GB
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)
                percent_used = usage.percent

                # Determine status
                status = determine_disk_status(free_gb, percent_used)

                # Build details
                details = json.dumps(
                    {
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(total_gb, 2),
                        "used_gb": round(used_gb, 2),
                        "free_gb": round(free_gb, 2),
                    }
                )

                # Sanitize mountpoint for metric name (replace / with _)
                mount_name = partition.mountpoint.replace("/", "_") or "_root"

                # Insert disk percentage metric
                await insert_metric_sample(
                    category="disk",
                    name=f"disk{mount_name}_percent",
                    value_num=percent_used,
                    status=status,
                    details_json=details,
                )

                # Insert disk free space in GB
                await insert_metric_sample(
                    category="disk",
                    name=f"disk{mount_name}_free_gb",
                    value_num=free_gb,
                    status=status,
                )

                disk_results[partition.mountpoint] = {
                    "total_gb": round(total_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent_used": percent_used,
                    "status": status,
                }

                logger.info(
                    f"Disk {partition.mountpoint}: {free_gb:.1f}GB free / {total_gb:.1f}GB total ({percent_used:.1f}% used) ({status})"
                )

            except (PermissionError, OSError) as e:
                logger.warning(
                    f"Cannot access disk {partition.mountpoint}: {e}"
                )
                continue

        return disk_results if disk_results else None

    except Exception as e:
        logger.error(f"Failed to collect disk metrics: {e}")
        return None


async def collect_all_system_metrics() -> dict:
    """
    Collect all system metrics (CPU, memory, disk) in one call.

    This is the main entry point for system monitoring. It calls all individual
    collectors and aggregates the results.

    Returns:
        Dict with all metrics and overall status
        Example: {
            "cpu": {...},
            "memory": {...},
            "disk": {...},
            "timestamp": "2026-01-25T10:30:00",
            "overall_status": "OK"
        }
    """
    timestamp = datetime.utcnow().isoformat()

    results = {
        "cpu": await collect_cpu_metrics(),
        "memory": await collect_memory_metrics(),
        "disk": await collect_disk_metrics(),
        "timestamp": timestamp,
    }

    # Determine overall status (worst status wins)
    statuses = []
    if results["cpu"]:
        statuses.append(results["cpu"]["status"])
    if results["memory"]:
        statuses.append(results["memory"]["status"])
    if results["disk"]:
        for disk_info in results["disk"].values():
            statuses.append(disk_info["status"])

    # Overall status priority: FAIL > WARN > OK
    if "FAIL" in statuses:
        overall_status = "FAIL"
    elif "WARN" in statuses:
        overall_status = "WARN"
    else:
        overall_status = "OK"

    results["overall_status"] = overall_status

    logger.info(f"System metrics collection complete: {overall_status}")

    return results
