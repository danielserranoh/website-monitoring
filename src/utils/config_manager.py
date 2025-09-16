"""
Configuration Manager

Centralized configuration handling with validation and defaults.
"""

import json
import os
from typing import Dict, Any, Optional


class ConfigManager:
    """Centralized configuration management"""

    def __init__(self):
        self._config = None
        self._config_file = None

    @classmethod
    def load_config(cls, config_file: str = 'config/config.json') -> Dict[str, Any]:
        """
        Load configuration from JSON file with validation.

        Args:
            config_file: Path to configuration file

        Returns:
            Dictionary containing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file has invalid JSON
        """
        instance = cls()
        instance._config_file = config_file

        try:
            with open(config_file, 'r') as f:
                instance._config = json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Using default configuration.")
            instance._config = instance._get_default_config()
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file {config_file}: {e}")
            raise

        # Validate configuration
        instance._validate_config()

        return instance._config

    def _validate_config(self) -> None:
        """Validate configuration structure and required fields"""
        required_sections = ['monitoring', 'system_monitoring', 'output', 'logging']

        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Validate monitoring section
        monitoring = self._config['monitoring']
        if not monitoring.get('target_url'):
            raise ValueError("target_url is required in monitoring configuration")

        # Ensure numeric values are valid
        if monitoring.get('reload_interval_seconds', 0) <= 0:
            raise ValueError("reload_interval_seconds must be positive")

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "monitoring": {
                "target_url": "",
                "reload_interval_seconds": 90,
                "page_timeout_ms": 30000,
                "headless_browser": False,
                "wait_for_networkidle": True
            },
            "system_monitoring": {
                "monitoring_interval_seconds": 5,
                "memory_spike_threshold_multiplier": 3,
                "cpu_threshold_percent": 80,
                "system_memory_critical_percent": 90,
                "network_monitoring_interval_seconds": 30
            },
            "memory_leak_detection": {
                "enabled": True,
                "sampling_window_minutes": 60,
                "detection_thresholds": {
                    "chrome_process_memory": {
                        "growth_rate_threshold_mb_per_min": 10,
                        "total_growth_threshold_mb": 500,
                        "percentage_growth_threshold": 200
                    },
                    "js_heap_memory": {
                        "growth_rate_threshold_mb_per_min": 5,
                        "no_gc_duration_threshold_seconds": 300,
                        "heap_fragmentation_threshold": 0.7
                    },
                    "per_reload_analysis": {
                        "memory_not_freed_threshold_mb": 50,
                        "cumulative_leak_per_reload_mb": 10
                    }
                },
                "trend_analysis": {
                    "short_term_window_seconds": 300,
                    "medium_term_window_seconds": 1800,
                    "long_term_window_seconds": 3600
                },
                "alert_sensitivity": "medium",
                "log_detailed_analysis": True
            },
            "suspect_services": {
                "curator": {
                    "keywords": ["curator", "social-network", "feed"],
                    "enabled": True
                },
                "cookieyes": {
                    "keywords": ["cookieyes", "cookie-consent", "cmp"],
                    "enabled": True
                },
                "serviceforce": {
                    "keywords": ["serviceforce", "whatsapp", "chat"],
                    "enabled": True
                }
            },
            "output": {
                "screenshots_enabled": True,
                "performance_logging": True,
                "console_logging": True,
                "reports_directory": "reports",
                "screenshots_directory": "screenshots",
                "logs_directory": "logs"
            },
            "logging": {
                "level": "INFO",
                "console_output": True,
                "file_output": True,
                "log_file": "monitoring.log"
            }
        }

    @classmethod
    def save_config(cls, config: Dict[str, Any], config_file: str = 'config/config.json') -> None:
        """
        Save configuration to JSON file.

        Args:
            config: Configuration dictionary to save
            config_file: Path to save configuration file
        """
        os.makedirs(os.path.dirname(config_file), exist_ok=True)

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    @classmethod
    def get_section(cls, config: Dict[str, Any], section: str, default: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get a configuration section with fallback to default.

        Args:
            config: Full configuration dictionary
            section: Section name to retrieve
            default: Default value if section doesn't exist

        Returns:
            Configuration section
        """
        return config.get(section, default or {})

    @classmethod
    def merge_configs(cls, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries, with override taking precedence.

        Args:
            base_config: Base configuration
            override_config: Configuration to override base with

        Returns:
            Merged configuration
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = cls.merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged