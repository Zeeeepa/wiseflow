"""
API endpoints for settings management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Define settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "data", "settings.json")

# Ensure data directory exists
os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)

# Settings models
class InterfaceSettings(BaseModel):
    dark_mode: bool = True
    compact_view: bool = True
    show_tooltips: bool = False
    refresh_rate: str = "30"

class DatabaseSettings(BaseModel):
    storage_location: str = "/data/findings"
    auto_backup: str = "daily"
    retention_period: str = "90"

class ProcessingSettings(BaseModel):
    max_parallel_tasks: str = "8"
    default_workers: str = "4"
    cpu_limit: str = "80"
    memory_limit: str = "70"

class GithubSettings(BaseModel):
    api_key: str = ""
    rate_limit: str = "5000 requests/hour"

class SearchEnginesSettings(BaseModel):
    google_api_key: str = ""
    bing_api_key: str = ""
    custom_search_id: str = ""

class YoutubeSettings(BaseModel):
    api_key: str = ""
    rate_limit: str = "10000 units/day"

class ArxivSettings(BaseModel):
    email: str = "user@example.com"
    rate_limit: str = "100 requests/minute"

class ApiKeysSettings(BaseModel):
    github: GithubSettings = GithubSettings()
    search_engines: SearchEnginesSettings = SearchEnginesSettings()
    youtube: YoutubeSettings = YoutubeSettings()
    arxiv: ArxivSettings = ArxivSettings()

class Settings(BaseModel):
    interface: InterfaceSettings = InterfaceSettings()
    database: DatabaseSettings = DatabaseSettings()
    processing: ProcessingSettings = ProcessingSettings()
    api_keys: ApiKeysSettings = ApiKeysSettings()

# Default settings
DEFAULT_SETTINGS = Settings()

def load_settings() -> Settings:
    """Load settings from file or return defaults."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return Settings(**data)
        return DEFAULT_SETTINGS
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS

def save_settings(settings: Settings) -> bool:
    """Save settings to file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings.dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

@router.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    """Get current settings."""
    settings = load_settings()
    return settings.dict()

@router.post("/api/settings")
async def update_settings(settings: Settings) -> Dict[str, Any]:
    """Update settings."""
    if save_settings(settings):
        return {"status": "success", "message": "Settings saved successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save settings")

@router.post("/api/settings/reset")
async def reset_settings() -> Dict[str, Any]:
    """Reset settings to defaults."""
    if save_settings(DEFAULT_SETTINGS):
        return {"status": "success", "message": "Settings reset to defaults"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reset settings")

