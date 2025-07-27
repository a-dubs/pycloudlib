"""Deal with configuration file."""

import logging
import os
from io import StringIO
from pathlib import Path
from typing import Any, Dict, MutableMapping, Optional, Union

import jsonschema
import toml

from pycloudlib.config_schemas import CLOUD_SCHEMAS

# Order matters here. Local should take precedence over global.
CONFIG_PATHS = [
    Path("~/.config/pycloudlib.toml").expanduser(),
    Path("/etc/pycloudlib.toml"),
]

ConfigFile = Union[Path, StringIO]
log = logging.getLogger(__name__)


class Config(dict):
    """Override dict to allow raising a more meaningful KeyError."""

    def __getitem__(self, key):
        """Provide more meaningful KeyError on access."""
        try:
            return super().__getitem__(key)
        except KeyError:
            raise KeyError(f"{key} must be defined in pycloudlib.toml to make this call") from None


def validate_cloud_config(cloud_type: str, config: Dict[str, Any]) -> None:
    """
    Validate cloud configuration against its schema.
    
    Args:
        cloud_type: The type of cloud (e.g., "ec2", "azure", etc.)
        config: The configuration dictionary to validate
        
    Raises:
        ValueError: If the configuration is invalid
    """
    if cloud_type not in CLOUD_SCHEMAS:
        log.warning(f"No schema available for cloud type '{cloud_type}', skipping validation")
        return
        
    schema = CLOUD_SCHEMAS[cloud_type]
    try:
        jsonschema.validate(config, schema)
        log.debug(f"Configuration for {cloud_type} passed validation")
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid configuration for {cloud_type}: {e.message}") from e


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries, with override_config taking precedence.
    
    Args:
        base_config: Base configuration (e.g., from TOML file)
        override_config: Override configuration (e.g., from constructor parameters)
        
    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()
    
    # Only update with non-None values from override
    for key, value in override_config.items():
        if value is not None:
            merged[key] = value
            
    return merged


def parse_config(
    config_file: Optional[ConfigFile] = None,
    validate: bool = True,
    cloud_type: Optional[str] = None,
) -> MutableMapping[str, Any]:
    """Find the relevant TOML, load, and return it.
    
    Args:
        config_file: Optional path to config file
        validate: Whether to validate the configuration against schemas
        cloud_type: Cloud type for validation (if validate=True)
        
    Returns:
        Configuration dictionary
    """
    possible_configs = []
    if config_file:
        possible_configs.append(config_file)
    if os.environ.get("PYCLOUDLIB_CONFIG"):
        possible_configs.append(Path(os.environ["PYCLOUDLIB_CONFIG"]))
    possible_configs.extend(CONFIG_PATHS)
    
    for path in possible_configs:
        try:
            config = toml.load(path, _dict=Config)
            log.debug("Loaded configuration from %s", path)
            
            # Validate configuration if requested and cloud_type is provided
            if validate and cloud_type and cloud_type in config:
                validate_cloud_config(cloud_type, config[cloud_type])
                
            return config
        except FileNotFoundError:
            continue
        except toml.TomlDecodeError as e:
            raise ValueError(f"Could not parse configuration file pointed to by {path}") from e
        except ValueError as e:
            # Re-raise validation errors with file context
            raise ValueError(f"Configuration validation failed for {path}: {e}") from e
            
    raise ValueError(
        "No configuration file found! Copy pycloudlib.toml.template to "
        "~/.config/pycloudlib.toml or /etc/pycloudlib.toml"
    )
