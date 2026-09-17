#!/usr/bin/env python3

"""Persistent settings for Hotspots & Landables Finder v8.

The v8 settings live under a dedicated key inside the existing
%APPDATA%\HotspotsFinder\config.json file so older configuration values are
preserved instead of being overwritten.
"""

import copy
import json
import os
from pathlib import Path


APP_DATA_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "HotspotsFinder"
CONFIG_PATH = APP_DATA_DIR / "config.json"
SETTINGS_KEY = "v8_settings"

DEFAULT_SETTINGS = {
    "startup": {
        "hotspots_enabled": True,
        "planets_enabled": True,
        "community_deposits_enabled": True,
        "max_distance_ly": 50.0,
        "remember_last_filters": False,
    },
    "rhinospotter": {
        # Empty means use the standard %LOCALAPPDATA%\RhinoSpotter\cards path.
        "cards_dir": "",
        "ask_before_sync": True,
    },
    "application": {
        "theme": "deep_black",
        "ui_scale": 1.15,
    },
    "last_filters": {},
}


def _merge_defaults(defaults, saved):
    result = copy.deepcopy(defaults)
    if not isinstance(saved, dict):
        return result

    for key, value in saved.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_defaults(result[key], value)
        else:
            result[key] = value
    return result


def _read_root_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_settings():
    root = _read_root_config()
    return _merge_defaults(DEFAULT_SETTINGS, root.get(SETTINGS_KEY, {}))


def save_settings(settings):
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    root = _read_root_config()
    root[SETTINGS_KEY] = _merge_defaults(DEFAULT_SETTINGS, settings)

    temp_path = CONFIG_PATH.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(root, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(CONFIG_PATH)


def default_rhinospotter_cards_dir():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "RhinoSpotter" / "cards"
    return Path.home() / "AppData" / "Local" / "RhinoSpotter" / "cards"


def resolve_rhinospotter_cards_dir(settings):
    custom = str(
        (settings or {}).get("rhinospotter", {}).get("cards_dir", "") or ""
    ).strip()
    if custom:
        return Path(custom).expanduser()
    return default_rhinospotter_cards_dir()
