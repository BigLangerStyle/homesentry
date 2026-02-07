"""
Module field definitions for configuration UI.

This module defines the form fields for each application module,
including field types, labels, validation rules, and help text.
"""

MODULE_FIELDS = {
    "homeassistant": {
        "display_name": "Home Assistant",
        "fields": [
            {
                "key": "api_url",
                "label": "API URL",
                "type": "text",
                "required": True,
                "default": "http://homeassistant:8123",
                "help": "Use container name if on same Docker network"
            },
            {
                "key": "api_token",
                "label": "API Token",
                "type": "password",
                "required": True,
                "sensitive": True,
                "help": "Generate from Home Assistant → Profile → Security → Long-Lived Access Tokens"
            },
            {
                "key": "entity_count_warn",
                "label": "Entity Count Warning Threshold",
                "type": "number",
                "required": False,
                "default": "500",
                "help": "Alert when total entities exceed this count"
            },
            {
                "key": "entity_count_fail",
                "label": "Entity Count Critical Threshold",
                "type": "number",
                "required": False,
                "default": "1000",
                "help": "Critical alert when total entities exceed this count"
            },
            {
                "key": "automation_count_warn",
                "label": "Automation Count Warning Threshold",
                "type": "number",
                "required": False,
                "default": "100",
                "help": "Alert when automation count exceeds this count"
            },
            {
                "key": "automation_count_fail",
                "label": "Automation Count Critical Threshold",
                "type": "number",
                "required": False,
                "default": "200",
                "help": "Critical alert when automation count exceeds this count"
            },
            {
                "key": "timeout",
                "label": "API Timeout (seconds)",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Timeout for API requests"
            }
        ]
    },
    "qbittorrent": {
        "display_name": "qBittorrent",
        "fields": [
            {
                "key": "api_url",
                "label": "Web UI URL",
                "type": "text",
                "required": True,
                "default": "http://qbittorrent:8080",
                "help": "Use container name if on same Docker network"
            },
            {
                "key": "username",
                "label": "Web UI Username",
                "type": "text",
                "required": True,
                "default": "admin",
                "help": "Default username is 'admin'"
            },
            {
                "key": "password",
                "label": "Web UI Password",
                "type": "password",
                "required": True,
                "sensitive": True,
                "default": "adminadmin",
                "help": "Change default password in qBittorrent → Tools → Options → Web UI"
            },
            {
                "key": "active_torrents_warn",
                "label": "Active Torrents Warning Threshold",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Warn when too many torrents are active"
            },
            {
                "key": "active_torrents_fail",
                "label": "Active Torrents Critical Threshold",
                "type": "number",
                "required": False,
                "default": "20",
                "help": "Critical alert when too many torrents are active"
            },
            {
                "key": "disk_free_warn_gb",
                "label": "Disk Free Warning (GB)",
                "type": "number",
                "required": False,
                "default": "100",
                "help": "Warn when download directory has less than this much free space"
            },
            {
                "key": "disk_free_fail_gb",
                "label": "Disk Free Critical (GB)",
                "type": "number",
                "required": False,
                "default": "50",
                "help": "Critical alert when download directory has less than this much free space"
            },
            {
                "key": "timeout",
                "label": "API Timeout (seconds)",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Timeout for API requests"
            }
        ]
    },
    "pihole": {
        "display_name": "Pi-hole",
        "fields": [
            {
                "key": "api_url",
                "label": "Admin API URL",
                "type": "text",
                "required": True,
                "default": "http://192.168.1.8:80",
                "help": "Use your Pi-hole's IP address or hostname"
            },
            {
                "key": "api_password",
                "label": "API Password (Pi-hole v6+)",
                "type": "password",
                "required": True,
                "sensitive": True,
                "help": "Get from Pi-hole web UI → Settings → API → Configure app password"
            },
            {
                "key": "bare_metal",
                "label": "Running as bare-metal (not Docker)",
                "type": "checkbox",
                "required": False,
                "default": "true",
                "help": "Set to true if Pi-hole is installed as a systemd service (not in Docker)"
            },
            {
                "key": "blocked_percent_warn",
                "label": "Blocked Percentage Warning Threshold",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Warn if Pi-hole is blocking less than this percentage"
            },
            {
                "key": "blocked_percent_fail",
                "label": "Blocked Percentage Critical Threshold",
                "type": "number",
                "required": False,
                "default": "5",
                "help": "Critical alert if Pi-hole is blocking less than this percentage"
            },
            {
                "key": "timeout",
                "label": "API Timeout (seconds)",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Timeout for API requests"
            }
        ]
    },
    "plex": {
        "display_name": "Plex Media Server",
        "fields": [
            {
                "key": "api_url",
                "label": "Server URL",
                "type": "text",
                "required": True,
                "default": "http://192.168.1.8:32400",
                "help": "Use your Plex server's IP address or hostname"
            },
            {
                "key": "api_token",
                "label": "X-Plex-Token",
                "type": "password",
                "required": True,
                "sensitive": True,
                "help": "Get from Plex Web → Account Settings → 'Show' under Plex Token"
            },
            {
                "key": "bare_metal",
                "label": "Running as bare-metal (not Docker)",
                "type": "checkbox",
                "required": False,
                "default": "true",
                "help": "Set to true if Plex is installed as a systemd service (not in Docker)"
            },
            {
                "key": "transcode_count_warn",
                "label": "Transcode Count Warning Threshold",
                "type": "number",
                "required": False,
                "default": "3",
                "help": "Warn when too many concurrent transcodes (CPU-intensive)"
            },
            {
                "key": "transcode_count_fail",
                "label": "Transcode Count Critical Threshold",
                "type": "number",
                "required": False,
                "default": "5",
                "help": "Critical alert when too many concurrent transcodes"
            },
            {
                "key": "timeout",
                "label": "API Timeout (seconds)",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Timeout for API requests"
            }
        ]
    },
    "jellyfin": {
        "display_name": "Jellyfin Media Server",
        "fields": [
            {
                "key": "api_url",
                "label": "Server URL",
                "type": "text",
                "required": True,
                "default": "http://192.168.1.8:8096",
                "help": "Use your Jellyfin server's IP address or hostname"
            },
            {
                "key": "api_key",
                "label": "API Key",
                "type": "password",
                "required": True,
                "sensitive": True,
                "help": "Generate from Jellyfin Dashboard → API Keys → New API Key"
            },
            {
                "key": "transcode_count_warn",
                "label": "Transcode Count Warning Threshold",
                "type": "number",
                "required": False,
                "default": "3",
                "help": "Warn when too many concurrent transcodes (CPU-intensive)"
            },
            {
                "key": "transcode_count_fail",
                "label": "Transcode Count Critical Threshold",
                "type": "number",
                "required": False,
                "default": "5",
                "help": "Critical alert when too many concurrent transcodes"
            },
            {
                "key": "timeout",
                "label": "API Timeout (seconds)",
                "type": "number",
                "required": False,
                "default": "10",
                "help": "Timeout for API requests"
            }
        ]
    }
}
