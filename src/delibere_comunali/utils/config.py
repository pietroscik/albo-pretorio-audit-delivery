"""
Configuration management module.
Handles environment variables, configuration files, and tenant-specific settings.

OPTIMIZATION: Added support for environment variables via python-dotenv.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from functools import lru_cache

# Try to import dotenv for environment variable management
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None

# Setup basic logging to avoid circular import
_basic_logger = logging.getLogger(__name__)
_basic_logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
_basic_logger.addHandler(_handler)

# Default configuration values
DEFAULT_CONFIG = {
    # Database
    "DB_HOST": "localhost",
    "DB_PORT": 5432,
    "DB_NAME": "albo_pretorio",
    "DB_USER": "postgres",
    "DB_PASSWORD": "",
    # Redis
    "REDIS_HOST": "localhost",
    "REDIS_PORT": 6379,
    "REDIS_PASSWORD": "",
    "REDIS_DB": 0,
    # OCR
    "TESSERACT_CMD": "/usr/bin/tesseract",
    "OCR_DPI": 300,
    "OCR_MAX_WORKERS": 4,
    # File System
    "DATA_DIR": "./data",
    "OUTPUT_DIR": "./output",
    "LOG_DIR": "./logs",
    "CACHE_DIR": "./cache",
    # API
    "API_HOST": "0.0.0.0",
    "API_PORT": 8000,
    "API_DEBUG": False,
    # Security
    "SECRET_KEY": "default_secret_key_change_me",
    "JWT_SECRET": "default_jwt_secret_change_me",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRE_MINUTES": 30,
    # Monitoring
    "PROMETHEUS_ENABLED": True,
    "PROMETHEUS_PORT": 9090,
    "GRAFANA_URL": "http://localhost:3000",
    # ML
    "MODEL_DIR": "./models",
    "MAX_FEATURES": 10000,
    "N_JOBS": -1,
    # Parallel Processing
    "MAX_PARALLEL_WORKERS": 4,
    "BATCH_SIZE": 10,
    # Logging
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "text",
    "LOG_FILE": "app.log",
}


class Config:
    """
    Configuration manager that loads settings from environment variables,
    configuration files, and provides type-safe access.
    """

    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_file: Path to YAML configuration file
            env_file: Path to .env file (if not using default)
        """
        self._config: Dict[str, Any] = {}
        self._loaded_files: list = []

        # Load .env file if available
        if DOTENV_AVAILABLE:
            if env_file:
                load_dotenv(env_file)
                self._loaded_files.append(env_file)
            else:
                # Try to load from default locations
                for env_path in [".env", "config/.env", "/workspace/config/.env"]:
                    if Path(env_path).exists():
                        load_dotenv(env_path)
                        self._loaded_files.append(env_path)
                        break

        # Load YAML config file if specified
        if config_file:
            self._load_yaml_config(config_file)

        # Initialize with default values
        self._config = DEFAULT_CONFIG.copy()

        # Override with environment variables
        self._override_with_env()

    def _load_yaml_config(self, config_file: str) -> None:
        """Load configuration from YAML file."""
        try:
            import yaml

            with open(config_file, "r") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    self._config.update(yaml_config)
                    self._loaded_files.append(config_file)
                    _basic_logger.info(f"Loaded configuration from {config_file}")
        except ImportError:
            _basic_logger.warning("PyYAML not available, skipping YAML config")
        except FileNotFoundError:
            _basic_logger.warning(f"Config file not found: {config_file}")
        except Exception as e:
            _basic_logger.error(f"Error loading config file {config_file}: {e}")

    def _override_with_env(self) -> None:
        """Override configuration with environment variables."""
        # Map environment variable names to config keys
        env_mapping = {
            # Database
            "DB_HOST": "DB_HOST",
            "DB_PORT": "DB_PORT",
            "DB_NAME": "DB_NAME",
            "DB_USER": "DB_USER",
            "DB_PASSWORD": "DB_PASSWORD",
            # Redis
            "REDIS_HOST": "REDIS_HOST",
            "REDIS_PORT": "REDIS_PORT",
            "REDIS_PASSWORD": "REDIS_PASSWORD",
            "REDIS_DB": "REDIS_DB",
            # OCR
            "TESSERACT_CMD": "TESSERACT_CMD",
            "OCR_DPI": "OCR_DPI",
            "OCR_MAX_WORKERS": "OCR_MAX_WORKERS",
            # File System
            "DATA_DIR": "DATA_DIR",
            "OUTPUT_DIR": "OUTPUT_DIR",
            "LOG_DIR": "LOG_DIR",
            "CACHE_DIR": "CACHE_DIR",
            # API
            "API_HOST": "API_HOST",
            "API_PORT": "API_PORT",
            "API_DEBUG": "API_DEBUG",
            # Security
            "SECRET_KEY": "SECRET_KEY",
            "JWT_SECRET": "JWT_SECRET",
            "JWT_ALGORITHM": "JWT_ALGORITHM",
            "JWT_EXPIRE_MINUTES": "JWT_EXPIRE_MINUTES",
            # Monitoring
            "PROMETHEUS_ENABLED": "PROMETHEUS_ENABLED",
            "PROMETHEUS_PORT": "PROMETHEUS_PORT",
            "GRAFANA_URL": "GRAFANA_URL",
            # ML
            "MODEL_DIR": "MODEL_DIR",
            "MAX_FEATURES": "MAX_FEATURES",
            "N_JOBS": "N_JOBS",
            # Parallel Processing
            "MAX_PARALLEL_WORKERS": "MAX_PARALLEL_WORKERS",
            "BATCH_SIZE": "BATCH_SIZE",
            # Logging
            "LOG_LEVEL": "LOG_LEVEL",
            "LOG_FORMAT": "LOG_FORMAT",
            "LOG_FILE": "LOG_FILE",
        }

        for config_key, env_var in env_mapping.items():
            if env_var in os.environ:
                # Convert type based on default value
                default_value = DEFAULT_CONFIG.get(config_key)
                if default_value is not None:
                    if isinstance(default_value, bool):
                        # Convert string to boolean
                        env_value = os.environ[env_var].lower()
                        self._config[config_key] = env_value in ("true", "1", "yes", "on")
                    elif isinstance(default_value, int):
                        self._config[config_key] = int(os.environ[env_var])
                    elif isinstance(default_value, float):
                        self._config[config_key] = float(os.environ[env_var])
                    else:
                        self._config[config_key] = os.environ[env_var]
                else:
                    self._config[config_key] = os.environ[env_var]

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get a configuration value as integer."""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a configuration value as float."""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a configuration value as boolean."""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_path(self, key: str, default: Optional[Union[str, Path]] = None) -> Path:
        """Get a configuration value as Path."""
        value = self.get(key, default)
        if value is None:
            return Path(default) if default else Path()
        return Path(value)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary."""
        return self._config.copy()

    def get_loaded_files(self) -> list:
        """Return list of loaded configuration files."""
        return self._loaded_files.copy()

    # Backward compatibility properties
    @property
    def data_dir(self) -> Path:
        """Backward compatibility: data_dir property."""
        return self.get_path("DATA_DIR")

    @property
    def output_dir(self) -> Path:
        """Backward compatibility: output_dir property."""
        return self.get_path("OUTPUT_DIR")

    @property
    def log_dir(self) -> Path:
        """Backward compatibility: log_dir property."""
        return self.get_path("LOG_DIR")

    @property
    def cache_dir(self) -> Path:
        """Backward compatibility: cache_dir property."""
        return self.get_path("CACHE_DIR")


# Backward compatibility alias
AppConfig = Config


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.

    Args:
        config_file: Optional path to YAML configuration file

    Returns:
        Global Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file)
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config_instance
    _config_instance = None


def get_tenant_dir(ente: str) -> Path:
    """
    Get the directory for a specific tenant (ente).

    Args:
        ente: Name of the tenant/ente

    Returns:
        Path to the tenant's directory
    """
    config = get_config()
    data_dir = config.get_path("DATA_DIR")
    return data_dir / ente


def get_db_connection_string() -> str:
    """
    Get the database connection string.

    Returns:
        Database connection string
    """
    config = get_config()

    return (
        f"postgresql://{config.get('DB_USER')}:{config.get('DB_PASSWORD')}"
        f"@{config.get('DB_HOST')}:{config.get('DB_PORT')}/{config.get('DB_NAME')}"
    )


def get_redis_connection_string() -> str:
    """
    Get the Redis connection string.

    Returns:
        Redis connection string
    """
    config = get_config()
    password = config.get("REDIS_PASSWORD")
    if password:

        return (
            f"redis://:{password}@{config.get('REDIS_HOST')}"
            f":{config.get('REDIS_PORT')}/{config.get('REDIS_DB')}"
        )
    return f"redis://{config.get('REDIS_HOST')}:{config.get('REDIS_PORT')}/{config.get('REDIS_DB')}"
