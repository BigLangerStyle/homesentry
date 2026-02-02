"""
Configuration management API routes.

Provides endpoints for reading, validating, and writing HomeSentry configuration.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import dotenv_values

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
    Get current configuration.
    
    Returns current .env configuration grouped by sections.
    Sensitive fields are masked.
    """
    try:
        env_path = Path(".env")
        if not env_path.exists():
            env_path = Path(".env.example")
        
        env_dict = dotenv_values(env_path)
        grouped = group_env_vars_by_section(env_dict)
        
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
    
    Validates and writes new configuration to .env file.
    """
    try:
        # Read current .env for preserving masked values
        env_path = Path(".env")
        current_env = dotenv_values(env_path) if env_path.exists() else {}
        
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
        
        # Write atomically
        tmp_path = Path(".env.tmp")
        tmp_path.write_text(env_content)
        tmp_path.rename(env_path)
        
        logger.info("Configuration updated successfully")
        
        return JSONResponse(content={
            "success": True,
            "path": str(env_path.absolute())
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
