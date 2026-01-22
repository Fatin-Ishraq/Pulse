"""
Pulse Configuration Manager.
Handles loading and saving of application settings.
"""
import copy
import os
import sys
from pathlib import Path
from typing import Any, Dict

# TOML Support
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

APP_NAME = "pulse"

DEFAULT_CONFIG = {
    "ui": {
        "theme": "nord",
    },
    "core": {
        "refresh_rate": 1.0,
    }
}

def get_config_dir() -> Path:
    """Return the platform-specific configuration directory."""
    if sys.platform == "win32":
        config_home = os.environ.get("APPDATA")
        if config_home is None:
             config_home = Path.home() / "AppData" / "Roaming"
        else:
             config_home = Path(config_home)
    else:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    
    config_dir = config_home / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_config_path() -> Path:
    return get_config_dir() / "config.toml"

def load_config() -> Dict[str, Any]:
    """Load configuration from disk, falling back to defaults if missing."""
    path = get_config_path()
    if not path.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(path, "rb") as f:
            user_config = tomllib.load(f)
        
        # Deep merge with defaults to ensure all keys exist
        config = copy.deepcopy(DEFAULT_CONFIG)
        
        for section, values in user_config.items():
            if section in config and isinstance(values, dict) and isinstance(config[section], dict):
                config[section].update(values)
            else:
                config[section] = values
                
        return config
    except Exception:
        # Return defaults on error (e.g. corrupted file)
        return copy.deepcopy(DEFAULT_CONFIG)

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to disk."""
    path = get_config_path()
    try:
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
    except Exception:
        pass
