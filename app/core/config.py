"""Configuration Loader and Path Formatter
Handles reading config.yaml, default fallbacks, and path templating.
"""

from __future__ import annotations
import os
import re
import time
from pathlib import Path
from typing import Any, Dict
import yaml

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0.0",
    "ui": {
        "theme": "breeze-dark",
        "font_family": "Noto Sans, Segoe UI, sans-serif",
        "code_font_family": "JetBrains Mono, Consolas, monospace",
        "accent_color": "#3daee9",
        "enable_vim_mode": True,
        "keyboard_hints": True,
        "animation_duration_ms": 150,
    },
    "archiving": {
        "enabled": True,
        "db_path": "data/archive.db",
        "stream_recording": {
            "enabled": True,
            "dir_template": "data/recordings/{upid}_{bvid}",
            "filename_template": "{bvid}_{cid}_{title}_{timestamp}.flv",
        },
        "metadata_archiving": {
            "enabled": True,
            "record_timeseries_interval_seconds": 60,
        },
        "comments_archiving": {
            "enabled": True,
        },
    },
    "identity": {
        "default_active_id": "default_user",
        "inherit_on_navigation": True,
        "auto_follow_message_prompt": True,
    },
    "offline": {
        "enable_offline_mode": True,
        "queue_path": "data/offline_queue.json",
        "auto_sync_on_reconnect": True,
    },
    "danmaku": {
        "engine": "bas_and_standard",
        "opacity": 0.85,
        "font_size": 24,
        "density_limit": 60,
        "speed_ratio": 1.0,
    },
}

import sys

def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        p = Path(config_path)
        if not p.is_absolute():
            base = get_base_dir()
            if (base / config_path).exists():
                p = base / config_path
        self.config_path = p
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return DEFAULT_CONFIG.copy()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    # Merge with default config
                    return self._deep_merge(DEFAULT_CONFIG.copy(), loaded)
        except Exception as e:
            print(f"[Config] Error loading config: {e}, using defaults")
        return DEFAULT_CONFIG.copy()

    def _deep_merge(self, base: dict, update: dict) -> dict:
        for k, v in update.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                base[k] = self._deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        val: Any = self.data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        val = self.data
        for k in keys[:-1]:
            if k not in val or not isinstance(val[k], dict):
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.data, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f"[Config] Failed to save config: {e}")

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitizes filename for cross-platform compatibility (Windows, Linux, macOS)."""
        # Replace forbidden chars: \ / : * ? " < > |
        cleaned = re.sub(r'[\\/*?:"<>|]', "_", str(name))
        return cleaned.strip()[:128]

    def format_path(self, template: str, context: Dict[str, Any]) -> Path:
        """
        Formats path with placeholders: {aid}, {bvid}, {cid}, {upid}, {title}, {timestamp}, etc.
        Applies sanitization to prevent illegal characters in paths.
        """
        safe_ctx = {}
        for k, v in context.items():
            safe_ctx[k] = self.sanitize_filename(str(v))
        
        if "timestamp" not in safe_ctx:
            safe_ctx["timestamp"] = str(int(time.time()))
        
        # Fill placeholders
        formatted = template
        for k, v in safe_ctx.items():
            formatted = formatted.replace(f"{{{k}}}", v)
            
        # Clean up any unresolved placeholders
        formatted = re.sub(r'\{[a-zA-Z0-9_]+\}', "unknown", formatted)
        return Path(formatted)

# Global configuration singleton
config_instance = Config()
