"""
Pulse Configuration Manager.

Loads and saves application settings. Values coming off disk are user-editable,
so everything is validated before it reaches the app - a bad refresh_rate used
to go straight into set_interval().
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

# Keep in sync with THEMES in pulse.app.
VALID_THEMES = (
    "nord",
    "dracula",
    "monokai",
    "textual-dark",
    "solarized-dark",
    "gruvbox",
)

# Below ~0.1s the sampling is mostly noise and the UI cannot keep up; above a
# minute the display is no longer live.
MIN_REFRESH_RATE = 0.1
MAX_REFRESH_RATE = 60.0
DEFAULT_REFRESH_RATE = 1.0
DEFAULT_THEME = "nord"

DEFAULT_CONFIG: Dict[str, Any] = {
    "ui": {
        "theme": DEFAULT_THEME,
    },
    "core": {
        "refresh_rate": DEFAULT_REFRESH_RATE,
    },
}


def default_config() -> Dict[str, Any]:
    """A fresh copy of the defaults.

    Always a copy: callers mutate the config they are handed, and handing out
    DEFAULT_CONFIG itself would let them rewrite the defaults for the process.
    """
    return copy.deepcopy(DEFAULT_CONFIG)


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


def validate_refresh_rate(value: Any) -> float:
    """Coerce a refresh rate into the supported range."""
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return DEFAULT_REFRESH_RATE
    if rate != rate:  # NaN
        return DEFAULT_REFRESH_RATE
    return max(MIN_REFRESH_RATE, min(MAX_REFRESH_RATE, rate))


def validate_theme(value: Any) -> str:
    """Fall back to the default theme if the configured one is unknown."""
    if isinstance(value, str) and value in VALID_THEMES:
        return value
    return DEFAULT_THEME


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a config with every known value checked and coerced in range."""
    config.setdefault("ui", {})
    config.setdefault("core", {})

    if not isinstance(config["ui"], dict):
        config["ui"] = {}
    if not isinstance(config["core"], dict):
        config["core"] = {}

    config["ui"]["theme"] = validate_theme(config["ui"].get("theme"))
    config["core"]["refresh_rate"] = validate_refresh_rate(
        config["core"].get("refresh_rate")
    )
    return config


def load_config() -> Dict[str, Any]:
    """Load configuration from disk, falling back to defaults if missing."""
    path = get_config_path()

    if not path.exists():
        config = default_config()
        save_config(config)
        return config

    try:
        with open(path, "rb") as f:
            user_config = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        # Corrupt or unreadable file - run on defaults rather than refusing to start.
        return default_config()

    config = default_config()
    for section, values in user_config.items():
        if isinstance(values, dict) and isinstance(config.get(section), dict):
            config[section].update(values)
        else:
            config[section] = values

    return validate_config(config)


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to disk. Returns False if it could not be written."""
    path = get_config_path()
    try:
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        return True
    except (OSError, TypeError):
        return False
