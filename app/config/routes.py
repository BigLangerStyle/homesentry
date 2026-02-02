"""
Configuration management API routes.

Provides endpoints for reading, validating, and writing HomeSentry configuration.
Configuration is read from environment variables (loaded by Docker Compose from .env).
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config.module_fields import MODULE_FIELDS

logger = logging.getLogger(__name__)

router = APIRouter()

# Define sensitive field suffixes for masking
SENSITIVE_SUFFIXES = ["_TOKEN", "_PASSWORD", "_API_KEY", "_WEBHOOK_URL"]


def is_sensitive_field(key: str) -> bool:
    """Check if a field is sensitive based on its key."""
    return any(key.upper().endswith(suffix) for suffix in SENSITIVE_SUFFIXES)


def mask_sensitive_value(value: str) -> str:
    """Mask a sensitive value for display."""
    return "***sensitive***" if value else ""


def group_env_vars_by_section(env_dict: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Group environment variables by section (core, modules, infrastructure, advanced).
    
    Args:
        env_dict: Dictionary of environment variables from .env file
        
    Returns:
        Dictionary with sections as keys, each containing grouped env vars
    """
    result = {
        "core": {},
        "modules": {},
        "infrastructure": {},
        "advanced": {}
    }
    
    # Core settings
    core_prefixes = ["DISCORD_", "POLL_", "LOG_", "DATABASE_"]
    for key, value in env_dict.items():
        if any(key.startswith(prefix) for prefix in core_prefixes):
            if is_sensitive_field(key):
                value = mask_sensitive_value(value)
            result["core"][key.lower()] = value
    
    # Module settings
    module_prefixes = ["HOMEASSISTANT_", "QBITTORRENT_", "PIHOLE_", "PLEX_", "JELLYFIN_"]
    for module_prefix in module_prefixes:
        module_name = module_prefix.rstrip("_").lower()
        module_vars = {}
        enabled = False
        
        for key, value in env_dict.items():
            if key.startswith(module_prefix):
                enabled = True
                field_name = key[len(module_prefix):].lower()
                if is_sensitive_field(key):
                    value = mask_sensitive_value(value)
                module_vars[field_name] = value
        
        if enabled:
            result["modules"][module_name] = {
                "enabled": True,
                **module_vars
            }
        else:
            result["modules"][module_name] = {
                "enabled": False
            }
    
    # Infrastructure settings
    infra_prefixes = ["CPU_", "MEMORY_", "DISK_", "DOCKER_", "SMART_", "RAID_", "SERVICE_", "CONTAINER_"]
    for key, value in env_dict.items():
        if any(key.startswith(prefix) for prefix in infra_prefixes):
            result["infrastructure"][key.lower()] = value
    
    # Advanced settings
    advanced_prefixes = ["ALERTS_", "ALERT_", "SLEEP_", "MAINTENANCE_", "GLOBAL_MAINTENANCE_"]
    for key, value in env_dict.items():
        if any(key.startswith(prefix) for prefix in advanced_prefixes):
            result["advanced"][key.lower()] = value
    
    return result


def validate_config(config: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """
    Validate configuration data.
    
    Args:
        config: Configuration dictionary with sections
        
    Returns:
        Tuple of (is_valid, errors_dict)
    """
    errors = {}
    
    # Validate core settings
    if "core" in config:
        core = config["core"]
        if "discord_webhook_url" in core:
            webhook = core["discord_webhook_url"]
            if webhook and webhook != "***sensitive***":
                if not webhook.startswith("https://discord.com/api/webhooks/"):
                    errors["core.discord_webhook_url"] = "Must start with https://discord.com/api/webhooks/"
    
    # Validate module settings
    if "modules" in config:
        for module_name, module_config in config["modules"].items():
            if not module_config.get("enabled", False):
                continue
            
            if module_name not in MODULE_FIELDS:
                continue
            
            # Check required fields for enabled modules
            for field_def in MODULE_FIELDS[module_name]["fields"]:
                if not field_def.get("required", False):
                    continue
                
                field_key = field_def["key"]
                field_value = module_config.get(field_key, "")
                
                # Skip validation if field is still masked
                if field_value == "***sensitive***":
                    continue
                
                if not field_value:
                    field_label = field_def.get("label", field_key)
                    errors[f"modules.{module_name}.{field_key}"] = f"{field_label} is required when module is enabled"
    
    return (len(errors) == 0, errors)


def build_env_content(config: Dict[str, Any], current_env: Dict[str, str]) -> str:
    """
    Build .env file content from configuration.
    
    Args:
        config: New configuration dictionary
        current_env: Current .env values (for preserving masked sensitive fields)
        
    Returns:
        Complete .env file content as string
    """
    lines = []
    
    # Header
    lines.append("# HomeSentry Configuration")
    lines.append("# Generated by Web Configuration UI")
    lines.append("# DO NOT commit .env file to Git (it contains secrets)")
    lines.append("")
    
    # Core section
    lines.append("# " + "=" * 76)
    lines.append("# Core Settings")
    lines.append("# " + "=" * 76)
    
    if "core" in config:
        for key, value in sorted(config["core"].items()):
            env_key = key.upper()
            # Preserve masked sensitive values
            if value == "***sensitive***" and env_key in current_env:
                value = current_env[env_key]
            lines.append(f"{env_key}={value}")
    
    lines.append("")
    
    # Modules section
    lines.append("# " + "=" * 76)
    lines.append("# Application Modules")
    lines.append("# " + "=" * 76)
    
    if "modules" in config:
        for module_name, module_config in sorted(config["modules"].items()):
            if not module_config.get("enabled", False):
                continue
            
            module_prefix = module_name.upper()
            lines.append("")
            lines.append(f"# {MODULE_FIELDS.get(module_name, {}).get('display_name', module_name)}")
            
            for key, value in sorted(module_config.items()):
                if key == "enabled":
                    continue
                env_key = f"{module_prefix}_{key.upper()}"
                # Preserve masked sensitive values
                if value == "***sensitive***" and env_key in current_env:
                    value = current_env[env_key]
                lines.append(f"{env_key}={value}")
    
    lines.append("")
    
    # Infrastructure section
    lines.append("# " + "=" * 76)
    lines.append("# Infrastructure Settings")
    lines.append("# " + "=" * 76)
    
    if "infrastructure" in config:
        for key, value in sorted(config["infrastructure"].items()):
            env_key = key.upper()
            lines.append(f"{env_key}={value}")
    
    lines.append("")
    
    # Advanced section
    lines.append("# " + "=" * 76)
    lines.append("# Advanced Settings")
    lines.append("# " + "=" * 76)
    
    if "advanced" in config:
        for key, value in sorted(config["advanced"].items()):
            env_key = key.upper()
            lines.append(f"{env_key}={value}")
    
    lines.append("")
    
    return "\n".join(lines)


@router.get("/api/config")
async def get_config() -> JSONResponse:
    """
    Get current configuration from environment variables.
    
    Returns current configuration grouped by sections.
    Sensitive fields are masked.
    
    Note: In Docker, environment variables are loaded from .env by docker-compose.
    This is the proper way to handle config in containerized apps.
    """
    try:
        # Read all environment variables
        env_dict = dict(os.environ)
        logger.info(f"Reading configuration from {len(env_dict)} environment variables")
        
        # Filter to only HomeSentry-related variables
        homesentry_vars = {
            k: v for k, v in env_dict.items()
            if any(k.startswith(prefix) for prefix in [
                "DISCORD_", "POLL_", "LOG_", "DATABASE_",
                "HOMEASSISTANT_", "QBITTORRENT_", "PIHOLE_", "PLEX_", "JELLYFIN_",
                "CPU_", "MEMORY_", "DISK_", "DOCKER_", "SMART_", "RAID_", "SERVICE_", "CONTAINER_",
                "ALERTS_", "ALERT_", "SLEEP_", "MAINTENANCE_", "GLOBAL_MAINTENANCE_"
            ])
        }
        
        logger.info(f"Found {len(homesentry_vars)} HomeSentry configuration variables")
        
        grouped = group_env_vars_by_section(homesentry_vars)
        
        return JSONResponse(content=grouped)
    
    except Exception as e:
        logger.error(f"Error reading config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ConfigUpdate(BaseModel):
    """Configuration update request model."""
    core: Dict[str, Any] = {}
    modules: Dict[str, Dict[str, Any]] = {}
    infrastructure: Dict[str, Any] = {}
    advanced: Dict[str, Any] = {}


@router.post("/api/config")
async def update_config(config: ConfigUpdate) -> JSONResponse:
    """
    Update configuration.
    
    Validates and writes new configuration to .env file on host.
    Also updates environment variables in the current process.
    
    Note: Docker Compose loads .env from the host directory, so we write there.
    Changes take effect immediately for the current process, and persist for next restart.
    """
    try:
        # In Docker, write to host .env (mounted or parent of app dir)
        # The .env file should be in the parent directory of the app code
        if Path("/app/.env").exists():
            env_path = Path("/app/.env")
        elif Path("/app").exists():
            # We're in Docker but .env doesn't exist yet, create it
            env_path = Path("/app/.env")
        else:
            # Local development
            env_path = Path(".env")
        
        # Read current environment variables for preserving masked values
        current_env = dict(os.environ)
        
        # Convert to dict for validation
        config_dict = config.dict()
        
        # Validate configuration
        is_valid, errors = validate_config(config_dict)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"success": False, "errors": errors}
            )
        
        # Build new .env content
        env_content = build_env_content(config_dict, current_env)
        
        # Write atomically to .env file
        tmp_path = env_path.parent / ".env.tmp"
        tmp_path.write_text(env_content)
        tmp_path.rename(env_path)
        
        # Also update the current process environment variables
        # This makes changes take effect immediately without restart
        # Parse the .env content we just wrote
        new_env = {}
        for line in env_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                new_env[key] = value
                os.environ[key] = value
        
        logger.info(f"Configuration updated successfully at {env_path}")
        logger.info(f"Updated {len(new_env)} environment variables in current process")
        
        return JSONResponse(content={
            "success": True,
            "path": str(env_path.absolute()),
            "message": "Configuration saved. Changes take effect immediately."
        })
    
    except Exception as e:
        logger.error(f"Error updating config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/validate")
async def validate_config_endpoint(config: ConfigUpdate) -> JSONResponse:
    """
    Validate configuration without saving.
    
    Returns validation results without writing to .env.
    """
    try:
        config_dict = config.dict()
        is_valid, errors = validate_config(config_dict)
        
        if is_valid:
            return JSONResponse(content={"valid": True})
        else:
            return JSONResponse(content={"valid": False, "errors": errors})
    
    except Exception as e:
        logger.error(f"Error validating config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/restart")
async def restart_container() -> JSONResponse:
    """
    Provide restart instructions.
    
    Returns command to restart the container (does not actually restart).
    """
    return JSONResponse(content={
        "message": "Restart required. Run: docker compose -f docker/docker-compose.yml restart homesentry"
    })
