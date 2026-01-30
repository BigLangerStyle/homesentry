"""
Collector modules for monitoring various system aspects.

Active collectors:
- system.py - CPU, RAM, disk usage
- services.py - HTTP health checks
- docker.py - Container monitoring
- smart.py - Drive health monitoring
- raid.py - RAID array status
- modules/ - App-specific monitoring plugins
"""

from .system import (
    collect_cpu_metrics,
    collect_memory_metrics,
    collect_disk_metrics,
    collect_all_system_metrics,
)
from .services import (
    check_service_health,
    check_all_services,
)
from .docker import (
    collect_all_docker_metrics,
)
from .smart import (
    collect_all_smart_metrics,
)
from .raid import (
    collect_all_raid_metrics,
)
from .modules.module_runner import (
    collect_all_app_metrics,
)

__all__ = [
    "collect_cpu_metrics",
    "collect_memory_metrics",
    "collect_disk_metrics",
    "collect_all_system_metrics",
    "check_service_health",
    "check_all_services",
    "collect_all_docker_metrics",
    "collect_all_smart_metrics",
    "collect_all_raid_metrics",
    "collect_all_app_metrics",
]
