#!/bin/bash

# HomeSentry Interactive Setup Installer
# This script walks you through configuring HomeSentry for the first time.
# It detects running services, guides you through configuration, and generates .env file.

set -u  # Exit on undefined variable

# ============================================================================
# Global Variables
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

# Dialog dimensions
DIALOG_HEIGHT=20
DIALOG_WIDTH=70
DIALOG_LIST_HEIGHT=12

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detection results (associative array)
declare -A DETECTED_SERVICES
declare -A SELECTED_MODULES
declare -A MODULE_CONFIGS

# Core configuration
DISCORD_WEBHOOK=""
POLL_INTERVAL=60

# Module display names and app names mapping
declare -A MODULE_DISPLAY_NAMES=(
    ["homeassistant"]="Home Assistant"
    ["qbittorrent"]="qBittorrent"
    ["pihole"]="Pi-hole"
    ["plex"]="Plex Media Server"
    ["jellyfin"]="Jellyfin Media Server"
)

# Container name patterns for detection
declare -A MODULE_CONTAINER_PATTERNS=(
    ["homeassistant"]="homeassistant|home-assistant"
    ["qbittorrent"]="qbittorrent|qbittorrent-vpn|qbittorrentvpn"
    ["pihole"]="pihole|pi-hole"
    ["plex"]="plex|plexmediaserver"
    ["jellyfin"]="jellyfin|jellyfin-server"
)

# Systemd service patterns for detection
declare -A MODULE_SYSTEMD_PATTERNS=(
    ["homeassistant"]="home-assistant|homeassistant"
    ["pihole"]="pihole|pi-hole"
    ["plex"]="plexmediaserver"
)

# HTTP check ports
declare -A MODULE_HTTP_PORTS=(
    ["homeassistant"]="8123"
    ["qbittorrent"]="8080"
    ["pihole"]="80"
    ["plex"]="32400"
    ["jellyfin"]="8096"
)

# Modules that support bare-metal operation
BARE_METAL_MODULES=("plex" "pihole")

# ============================================================================
# Utility Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    # Check for whiptail or dialog
    if command -v whiptail >/dev/null 2>&1; then
        DIALOG_CMD="whiptail"
    elif command -v dialog >/dev/null 2>&1; then
        DIALOG_CMD="dialog"
    else
        log_error "Neither whiptail nor dialog is installed."
        echo "Please install one of them:"
        echo "  Ubuntu/Debian: sudo apt-get install whiptail"
        echo "  RHEL/CentOS: sudo yum install newt (provides whiptail)"
        exit 1
    fi
    
    log_info "Using dialog tool: $DIALOG_CMD"
}

# ============================================================================
# Service Detection Functions
# ============================================================================

detect_docker_services() {
    log_info "Checking for Docker containers..."
    
    if ! command -v docker >/dev/null 2>&1; then
        log_warn "Docker command not found, skipping container detection"
        return
    fi
    
    # Check if we can access Docker
    if ! docker ps >/dev/null 2>&1; then
        log_warn "Cannot access Docker (permission denied or daemon not running)"
        return
    fi
    
    # Get list of running container names
    local containers
    containers=$(docker ps --format '{{.Names}}' 2>/dev/null || true)
    
    if [ -z "$containers" ]; then
        log_info "No running Docker containers found"
        return
    fi
    
    # Check each module's container patterns
    for module in "${!MODULE_CONTAINER_PATTERNS[@]}"; do
        local pattern="${MODULE_CONTAINER_PATTERNS[$module]}"
        if echo "$containers" | grep -qiE "$pattern"; then
            DETECTED_SERVICES["$module"]="docker"
            log_info "Detected $module via Docker"
        fi
    done
}

detect_systemd_services() {
    log_info "Checking for systemd services..."
    
    if ! command -v systemctl >/dev/null 2>&1; then
        log_warn "systemctl not found, skipping systemd detection"
        return
    fi
    
    # Get list of running services
    local services
    services=$(systemctl list-units --type=service --state=running --no-pager --plain 2>/dev/null | awk '{print $1}' || true)
    
    if [ -z "$services" ]; then
        log_warn "Could not query systemd services"
        return
    fi
    
    # Check each module's systemd patterns
    for module in "${!MODULE_SYSTEMD_PATTERNS[@]}"; do
        local pattern="${MODULE_SYSTEMD_PATTERNS[$module]}"
        if echo "$services" | grep -qiE "$pattern"; then
            DETECTED_SERVICES["$module"]="systemd"
            log_info "Detected $module via systemd"
        fi
    done
}

detect_http_services() {
    log_info "Checking for HTTP services..."
    
    if ! command -v curl >/dev/null 2>&1; then
        log_warn "curl not found, skipping HTTP detection"
        return
    fi
    
    # Check each module's HTTP port
    for module in "${!MODULE_HTTP_PORTS[@]}"; do
        local port="${MODULE_HTTP_PORTS[$module]}"
        local http_code
        
        # Try localhost first
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 5 "http://localhost:$port" 2>/dev/null || echo "000")
        
        # Accept any 2xx, 3xx, 4xx response (service is responding)
        if [[ "$http_code" =~ ^[234] ]]; then
            # Don't overwrite if already detected via docker/systemd
            if [ -z "${DETECTED_SERVICES[$module]:-}" ]; then
                DETECTED_SERVICES["$module"]="http"
                log_info "Detected $module via HTTP (port $port)"
            fi
        fi
    done
}

detect_all_services() {
    log_info "Starting service detection..."
    echo ""
    
    detect_docker_services
    detect_systemd_services
    detect_http_services
    
    echo ""
    log_info "Service detection complete"
}

# ============================================================================
# Screen 1: Welcome
# ============================================================================

show_welcome() {
    local message="Welcome to HomeSentry Setup Installer!

HomeSentry is a self-hosted health monitoring dashboard for home servers.
This installer will:

1. Detect running services on your system
2. Guide you through selecting services to monitor
3. Configure authentication and thresholds
4. Generate a ready-to-use .env configuration file

The entire process takes 5-10 minutes."
    
    # Check if .env already exists
    if [ -f "$ENV_FILE" ]; then
        message="$message

⚠️  WARNING: $ENV_FILE already exists!

Running this installer will OVERWRITE your existing configuration.
All current settings will be lost.

Do you want to continue?"
    fi
    
    if $DIALOG_CMD --title "HomeSentry Setup" --yesno "$message" $DIALOG_HEIGHT $DIALOG_WIDTH; then
        return 0
    else
        log_info "Setup cancelled by user"
        exit 0
    fi
}

# ============================================================================
# Screen 2: Service Detection Results
# ============================================================================

show_detection_results() {
    local detected_list=""
    local count=0
    
    for module in "${!DETECTED_SERVICES[@]}"; do
        local display_name="${MODULE_DISPLAY_NAMES[$module]}"
        local method="${DETECTED_SERVICES[$module]}"
        detected_list="$detected_list\n  • $display_name (detected via $method)"
        ((count++))
    done
    
    if [ $count -eq 0 ]; then
        detected_list="No services detected automatically.\n\nYou can still manually select services to monitor."
    else
        detected_list="Found $count service(s):$detected_list"
    fi
    
    if ! $DIALOG_CMD --title "Service Detection" --msgbox "$detected_list\n\nPress OK to continue to service selection." $DIALOG_HEIGHT $DIALOG_WIDTH; then
        log_info "Setup cancelled by user"
        exit 0
    fi
}

# ============================================================================
# Screen 3: Module Selection
# ============================================================================

show_module_selection() {
    local options=()
    
    # Build checklist options (module_key "Display Name" status)
    for module in homeassistant qbittorrent pihole plex jellyfin; do
        local display_name="${MODULE_DISPLAY_NAMES[$module]}"
        local status="OFF"
        local detection_info="not detected"
        
        # Check if detected
        if [ -n "${DETECTED_SERVICES[$module]:-}" ]; then
            status="ON"
            local method="${DETECTED_SERVICES[$module]}"
            if [ "$method" = "docker" ]; then
                detection_info="Docker container"
            elif [ "$method" = "systemd" ]; then
                detection_info="systemd service"
            else
                detection_info="HTTP responding"
            fi
        fi
        
        options+=("$module" "$display_name - $detection_info" "$status")
    done
    
    # Show checklist
    local selected
    local exit_code
    selected=$($DIALOG_CMD --title "Select Services to Monitor" \
        --checklist "Use SPACE to select/deselect, ENTER to confirm:" \
        $DIALOG_HEIGHT $DIALOG_WIDTH $DIALOG_LIST_HEIGHT \
        "${options[@]}" \
        3>&1 1>&2 2>&3)
    exit_code=$?
    
    # Check if user cancelled
    if [ $exit_code -ne 0 ]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
    
    # Parse selected modules (removes quotes)
    selected=$(echo "$selected" | tr -d '"')
    
    log_info "Raw selected modules: $selected"
    
    # Clear previous selections (don't reinitialize as array, already associative)
    for module in homeassistant qbittorrent pihole plex jellyfin; do
        unset SELECTED_MODULES["$module"]
    done
    
    # Store selected modules
    local selected_count=0
    for module in $selected; do
        SELECTED_MODULES["$module"]=1
        log_info "Selected module: $module"
        ((selected_count++))
    done
    
    if [ $selected_count -eq 0 ]; then
        $DIALOG_CMD --title "No Services Selected" \
            --msgbox "You must select at least one service to monitor.\n\nReturning to service selection..." \
            10 60
        show_module_selection
        return
    fi
}

# ============================================================================
# Screen 4: Core Configuration
# ============================================================================

test_discord_webhook() {
    local webhook_url="$1"
    
    log_info "Testing Discord webhook..."
    
    local payload='{
  "embeds": [{
    "title": "🧪 Test Alert - HomeSentry",
    "description": "If you can see this, Discord alerts are working correctly!",
    "color": 5814783,
    "fields": [
      {"name": "Status", "value": "✅ Configuration Valid", "inline": true},
      {"name": "Webhook", "value": "Connected Successfully", "inline": true}
    ]
  }]
}'
    
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$webhook_url" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        2>/dev/null || echo "000")
    
    if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
        $DIALOG_CMD --title "Webhook Test" --msgbox "✅ Webhook test successful!\n\nCheck your Discord channel for the test message." 10 60
        return 0
    else
        $DIALOG_CMD --title "Webhook Test Failed" --msgbox "❌ Webhook test failed (HTTP $http_code)\n\nPlease check:\n• URL is correct\n• Webhook hasn't been deleted\n• Network connectivity\n\nYou can continue anyway and fix it later." 12 60
        return 1
    fi
}

show_core_config() {
    # Get Discord webhook URL
    local webhook_default="https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE"
    local exit_code
    
    DISCORD_WEBHOOK=$($DIALOG_CMD --title "Discord Webhook URL" \
        --inputbox "Enter your Discord webhook URL:\n\n(Create in Discord: Server Settings > Integrations > Webhooks)" \
        12 $DIALOG_WIDTH "$webhook_default" \
        3>&1 1>&2 2>&3)
    exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
    
    # Validate webhook URL format
    if [[ ! "$DISCORD_WEBHOOK" =~ ^https://discord.com/api/webhooks/ ]]; then
        $DIALOG_CMD --title "Invalid Webhook URL" \
            --msgbox "The webhook URL must start with:\nhttps://discord.com/api/webhooks/\n\nPlease try again." \
            10 60
        show_core_config
        return
    fi
    
    # Offer to test webhook
    if $DIALOG_CMD --title "Test Webhook" \
        --yesno "Do you want to test the Discord webhook now?\n\nThis will send a test message to your Discord channel." \
        10 60; then
        test_discord_webhook "$DISCORD_WEBHOOK"
    fi
    
    # Get polling interval
    POLL_INTERVAL=$($DIALOG_CMD --title "Polling Interval" \
        --inputbox "How often should HomeSentry check services?\n\n(Enter interval in seconds, default: 60)" \
        12 $DIALOG_WIDTH "60" \
        3>&1 1>&2 2>&3)
    exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
    
    # Validate polling interval is a number
    if ! [[ "$POLL_INTERVAL" =~ ^[0-9]+$ ]]; then
        $DIALOG_CMD --title "Invalid Input" --msgbox "Polling interval must be a number.\n\nUsing default: 60 seconds" 10 60
        POLL_INTERVAL=60
    fi
    
    log_info "Core configuration: webhook set, poll interval = $POLL_INTERVAL"
}

# ============================================================================
# Module Configuration Field Definitions
# ============================================================================

# Format: env_suffix|label|type|required|default
# type: text, password, number
# required: required, optional

get_module_fields() {
    local module=$1
    
    case $module in
        homeassistant)
            echo "api_url|API URL|text|required|http://homeassistant:8123"
            echo "api_token|Long-Lived Access Token|password|required|"
            echo "entity_count_warn|Entity Count Warning Threshold [Optional]|number|optional|500"
            echo "entity_count_fail|Entity Count Fail Threshold [Optional]|number|optional|1000"
            echo "automation_count_warn|Automation Count Warning [Optional]|number|optional|100"
            echo "automation_count_fail|Automation Count Fail [Optional]|number|optional|200"
            echo "timeout|API Timeout in Seconds [Optional]|number|optional|10"
            ;;
        qbittorrent)
            echo "api_url|API URL|text|required|http://qbittorrent:8080"
            echo "username|Web UI Username|text|required|admin"
            echo "password|Web UI Password|password|required|adminadmin"
            echo "active_torrents_warn|Active Torrents Warning [Optional]|number|optional|10"
            echo "active_torrents_fail|Active Torrents Fail [Optional]|number|optional|20"
            echo "disk_free_warn_gb|Disk Free Warning GB [Optional]|number|optional|100"
            echo "disk_free_fail_gb|Disk Free Fail GB [Optional]|number|optional|50"
            echo "timeout|API Timeout in Seconds [Optional]|number|optional|10"
            ;;
        pihole)
            echo "api_url|API URL|text|required|http://192.168.1.8:80"
            echo "api_password|App Password (Pi-hole v6+)|password|required|"
            echo "blocked_percent_warn|Blocked Percent Warning [Optional]|number|optional|10"
            echo "blocked_percent_fail|Blocked Percent Fail [Optional]|number|optional|5"
            echo "timeout|API Timeout in Seconds [Optional]|number|optional|10"
            ;;
        plex)
            echo "api_url|API URL|text|required|http://192.168.1.8:32400"
            echo "api_token|X-Plex-Token|password|required|"
            echo "transcode_count_warn|Transcode Count Warning [Optional]|number|optional|3"
            echo "transcode_count_fail|Transcode Count Fail [Optional]|number|optional|5"
            echo "timeout|API Timeout in Seconds [Optional]|number|optional|10"
            ;;
        jellyfin)
            echo "api_url|API URL|text|required|http://192.168.1.8:8096"
            echo "api_key|API Key|password|required|"
            echo "transcode_count_warn|Transcode Count Warning [Optional]|number|optional|3"
            echo "transcode_count_fail|Transcode Count Fail [Optional]|number|optional|5"
            echo "timeout|API Timeout in Seconds [Optional]|number|optional|10"
            ;;
    esac
}

# ============================================================================
# Screen 5: Module Configuration
# ============================================================================

show_module_config() {
    local module=$1
    local display_name="${MODULE_DISPLAY_NAMES[$module]}"
    
    log_info "Configuring module: $module"
    
    # Initialize config storage for this module
    MODULE_CONFIGS["${module}_bare_metal"]="false"
    
    # Check if this module supports bare-metal
    local is_bare_metal_capable=0
    for bm_module in "${BARE_METAL_MODULES[@]}"; do
        if [ "$bm_module" = "$module" ]; then
            is_bare_metal_capable=1
            break
        fi
    done
    
    # If bare-metal capable, ask how it's running
    if [ $is_bare_metal_capable -eq 1 ]; then
        if $DIALOG_CMD --title "$display_name Configuration" \
            --yesno "How is $display_name running?\n\nSelect:\n• Yes = Docker container\n• No = Bare-metal (systemd service)" \
            12 60; then
            MODULE_CONFIGS["${module}_bare_metal"]="false"
            log_info "$module running in Docker"
        else
            MODULE_CONFIGS["${module}_bare_metal"]="true"
            log_info "$module running as bare-metal service"
        fi
    fi
    
    # Get field definitions
    local fields
    fields=$(get_module_fields "$module")
    
    # Process each field
    while IFS='|' read -r suffix label field_type requirement default_value; do
        local full_label="$label"
        
        # Add [Optional] indicator if not already in label
        if [ "$requirement" = "optional" ] && [[ ! "$label" =~ \[Optional\] ]]; then
            full_label="$label [Optional]"
        fi
        
        # Input type based on field type
        local input_type="--inputbox"
        if [ "$field_type" = "password" ]; then
            input_type="--passwordbox"
        fi
        
        # Prompt for value
        local value
        local exit_code
        value=$($DIALOG_CMD --title "$display_name Configuration" \
            $input_type "$full_label:" \
            10 $DIALOG_WIDTH "$default_value" \
            3>&1 1>&2 2>&3)
        exit_code=$?
        
        if [ $exit_code -ne 0 ]; then
            log_info "Setup cancelled by user"
            exit 0
        fi
        
        # Validate required fields
        if [ "$requirement" = "required" ] && [ -z "$value" ]; then
            $DIALOG_CMD --title "Required Field" \
                --msgbox "This field is required.\n\nPlease enter a value for:\n$label" \
                10 60
            show_module_config "$module"
            return
        fi
        
        # Store the value (even if empty for optional fields)
        local env_key="${module}_${suffix}"
        MODULE_CONFIGS["$env_key"]="$value"
        
        log_info "Set $env_key = ${value:0:20}..." # Log first 20 chars only
        
    done <<< "$fields"
    
    log_info "Module $module configured successfully"
}

# ============================================================================
# Configuration File Generation
# ============================================================================

generate_env_content() {
    local content=""
    
    # Header
    content+="# HomeSentry Configuration\n"
    content+="# Generated by setup installer on $(date)\n"
    content+="# DO NOT commit this file to Git (it contains secrets)\n\n"
    
    # ========================================================================
    # Core Configuration
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Discord Alerts\n"
    content+="# ============================================================================\n"
    content+="DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK\n"
    content+="ALERTS_ENABLED=true\n"
    content+="ALERT_COOLDOWN_MINUTES=30\n\n"
    
    # ========================================================================
    # Polling Intervals
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Polling Intervals (seconds)\n"
    content+="# ============================================================================\n"
    content+="POLL_INTERVAL=$POLL_INTERVAL\n"
    content+="SMART_POLL_INTERVAL=600\n"
    content+="RAID_POLL_INTERVAL=300\n\n"
    
    # ========================================================================
    # Infrastructure Monitoring (defaults from .env.example)
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Alert Thresholds\n"
    content+="# ============================================================================\n"
    content+="# (defaults from .env.example — edit manually if needed)\n\n"
    
    content+="# CPU monitoring\n"
    content+="CPU_WARN_THRESHOLD=80\n"
    content+="CPU_FAIL_THRESHOLD=95\n\n"
    
    content+="# Memory monitoring\n"
    content+="MEMORY_WARN_THRESHOLD=85\n"
    content+="MEMORY_FAIL_THRESHOLD=95\n\n"
    
    content+="# Disk space warnings\n"
    content+="DISK_WARN_PERCENT=85\n"
    content+="DISK_FAIL_PERCENT=95\n"
    content+="DISK_WARN_GB=50\n"
    content+="DISK_FAIL_GB=10\n\n"
    
    content+="# Service health monitoring\n"
    content+="SERVICE_DOWN_WINDOW=120\n"
    content+="SERVICE_CHECK_TIMEOUT=10\n"
    content+="SERVICE_SLOW_THRESHOLD=3000\n\n"
    
    content+="# Container restart monitoring\n"
    content+="CONTAINER_RESTART_THRESHOLD=5\n\n"
    
    # ========================================================================
    # Database
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Database\n"
    content+="# ============================================================================\n"
    content+="DATABASE_PATH=/app/data/homesentry.db\n\n"
    
    # ========================================================================
    # Logging
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Logging\n"
    content+="# ============================================================================\n"
    content+="LOG_LEVEL=INFO\n\n"
    
    # ========================================================================
    # Docker Container Monitoring
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Docker Container Monitoring\n"
    content+="# ============================================================================\n"
    content+="# (defaults from .env.example — edit manually if needed)\n"
    content+="DOCKER_SOCKET_PATH=/var/run/docker.sock\n"
    content+="DOCKER_COLLECTION_ENABLED=true\n"
    content+="DOCKER_CPU_WARN_THRESHOLD=80\n"
    content+="DOCKER_CPU_FAIL_THRESHOLD=95\n"
    content+="DOCKER_MEMORY_WARN_THRESHOLD=80\n"
    content+="DOCKER_MEMORY_FAIL_THRESHOLD=95\n\n"
    
    # ========================================================================
    # SMART Drive Health Monitoring
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# SMART Drive Health Monitoring\n"
    content+="# ============================================================================\n"
    content+="# (defaults from .env.example — edit manually if needed)\n"
    content+="SMART_COLLECTION_ENABLED=true\n"
    content+="SMART_DEVICES=/dev/sda,/dev/sdb,/dev/sdc,/dev/sdd\n"
    content+="SMART_TEMP_WARN_THRESHOLD=50\n"
    content+="SMART_TEMP_FAIL_THRESHOLD=60\n\n"
    
    # ========================================================================
    # RAID Array Monitoring
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# RAID Array Monitoring\n"
    content+="# ============================================================================\n"
    content+="# (defaults from .env.example — edit manually if needed)\n"
    content+="RAID_COLLECTION_ENABLED=true\n"
    content+="RAID_ARRAYS=md0\n\n"
    
    # ========================================================================
    # Sleep Schedule & Morning Summary
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Sleep Schedule & Morning Summary\n"
    content+="# ============================================================================\n"
    content+="# (defaults from .env.example — edit manually if needed)\n"
    content+="SLEEP_SCHEDULE_ENABLED=false\n"
    content+="SLEEP_SCHEDULE_START=00:00\n"
    content+="SLEEP_SCHEDULE_END=07:30\n"
    content+="SLEEP_SUMMARY_ENABLED=true\n"
    content+="SLEEP_SUMMARY_TIME=07:30\n"
    content+="SLEEP_ALLOW_CRITICAL_ALERTS=false\n\n"
    
    # ========================================================================
    # Application Modules (only selected ones)
    # ========================================================================
    content+="# ============================================================================\n"
    content+="# Application Modules\n"
    content+="# ============================================================================\n\n"
    
    # Generate config for each selected module
    for module in homeassistant qbittorrent pihole plex jellyfin; do
        if [ "${SELECTED_MODULES[$module]:-0}" = "1" ]; then
            local display_name="${MODULE_DISPLAY_NAMES[$module]}"
            local module_upper=$(echo "$module" | tr '[:lower:]' '[:upper:]')
            
            content+="# ----------------------------------------------------------------------------\n"
            content+="# $display_name Module\n"
            content+="# ----------------------------------------------------------------------------\n"
            
            # Add bare_metal flag if applicable
            local bare_metal="${MODULE_CONFIGS[${module}_bare_metal]:-false}"
            if [ "$bare_metal" = "true" ]; then
                content+="${module_upper}_BARE_METAL=true\n"
            fi
            
            # Add all configured fields
            get_module_fields "$module" | while IFS='|' read -r suffix label field_type requirement default_value; do
                local env_key="${module}_${suffix}"
                local value="${MODULE_CONFIGS[$env_key]:-}"
                
                # Skip empty optional fields
                if [ "$requirement" = "optional" ] && [ -z "$value" ]; then
                    continue
                fi
                
                # Build full env var name
                local suffix_upper=$(echo "$suffix" | tr '[:lower:]' '[:upper:]')
                content+="${module_upper}_${suffix_upper}=$value\n"
            done
            
            content+="\n"
        fi
    done
    
    echo -e "$content"
}

write_env_file() {
    local preview_file="/tmp/homesentry_env_preview.txt"
    
    # Generate content
    local content
    content=$(generate_env_content)
    
    # Write to temporary preview file
    echo -e "$content" > "$preview_file"
    
    # Show preview
    $DIALOG_CMD --title "Review Configuration" \
        --textbox "$preview_file" \
        $DIALOG_HEIGHT $DIALOG_WIDTH
    
    # Confirm write
    if $DIALOG_CMD --title "Write Configuration" \
        --yesno "Write this configuration to .env file?\n\nLocation: $ENV_FILE" \
        10 $DIALOG_WIDTH; then
        
        # Write to .env
        echo -e "$content" > "$ENV_FILE"
        
        local abs_path=$(realpath "$ENV_FILE")
        log_info "Configuration written to: $abs_path"
        
        # Show success message with next steps
        $DIALOG_CMD --title "Setup Complete" --msgbox "✅ Configuration written to .env

Next steps:

1. Start HomeSentry:
   cd $(dirname "$abs_path")
   docker compose -f docker/docker-compose.yml up -d

2. View dashboard:
   http://YOUR_SERVER_IP:8000

3. Check logs:
   docker compose -f docker/docker-compose.yml logs -f

HomeSentry will start monitoring your services immediately!" \
            20 $DIALOG_WIDTH
        
        rm -f "$preview_file"
        return 0
    else
        log_info "User chose not to write configuration"
        rm -f "$preview_file"
        return 1
    fi
}

# ============================================================================
# Main Orchestration
# ============================================================================

main() {
    log_info "HomeSentry Setup Installer"
    log_info "Repository root: $REPO_ROOT"
    
    # Check dependencies first
    check_dependencies
    log_info "Dependencies checked"
    
    # Screen 1: Welcome
    show_welcome
    log_info "Welcome screen completed"
    
    # Screen 2: Service Detection
    detect_all_services
    show_detection_results
    log_info "Detection screen completed"
    
    # Screen 3: Module Selection
    log_info "Starting module selection..."
    show_module_selection
    log_info "Module selection completed. Selected modules: ${!SELECTED_MODULES[@]}"
    
    # Screen 4: Core Configuration
    log_info "Starting core configuration..."
    show_core_config
    log_info "Core configuration completed"
    
    # Screen 5: Module Configuration (one screen per selected module)
    for module in homeassistant qbittorrent pihole plex jellyfin; do
        if [ "${SELECTED_MODULES[$module]:-0}" = "1" ]; then
            log_info "Configuring module: $module"
            show_module_config "$module"
        fi
    done
    log_info "Module configuration completed"
    
    # Screen 6: Review & Write
    log_info "Starting review & write..."
    write_env_file
    
    log_info "Setup complete!"
}

# Run main if script is executed (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
