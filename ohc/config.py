"""
Configuration management for OpenHands Cloud CLI.

Handles server configuration storage and retrieval following XDG Base Directory
Specification.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, cast


class ConfigManager:
    """
    Manages OpenHands Cloud CLI configuration.

    Handles server configuration storage and retrieval with secure file permissions.
    Configuration is stored in JSON format following XDG Base Directory Specification.

    Attributes:
        config_dir: Path to configuration directory
        config_file: Path to configuration file
    """

    def __init__(self) -> None:
        """Initialize configuration manager and ensure config directory exists."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_dir(self) -> Path:
        """
        Get configuration directory following XDG Base Directory Specification.

        Returns:
            Path to configuration directory (~/.config/ohc or $XDG_CONFIG_HOME/ohc)
        """
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "ohc"
        return Path.home() / ".config" / "ohc"

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Dictionary containing configuration data with servers and default_server

        Raises:
            Exception: If configuration file cannot be read or parsed
        """
        if not self.config_file.exists():
            return {"servers": {}, "default_server": None}

        try:
            with open(self.config_file) as f:
                return cast("Dict[str, Any]", json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to load configuration: {e}") from e

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file with secure permissions.

        Args:
            config: Configuration dictionary to save

        Raises:
            Exception: If configuration file cannot be written
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            # Set restrictive permissions for security
            os.chmod(self.config_file, 0o600)
        except OSError as e:
            raise Exception(f"Failed to save configuration: {e}") from e

    def get_server_config(
        self, server_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server or the default server."""
        config = self.load_config()

        if server_name:
            return cast("Optional[Dict[str, Any]]", config["servers"].get(server_name))

        # Return default server if no specific server requested
        default_server = config.get("default_server")
        if default_server and default_server in config["servers"]:
            return cast("Dict[str, Any]", config["servers"][default_server])

        # If no default set, return the first server if any exist
        if config["servers"]:
            return cast("Dict[str, Any]", next(iter(config["servers"].values())))

        return None

    def add_server(
        self, name: str, url: str, api_key: str, set_default: bool = False
    ) -> None:
        """Add a new server configuration."""
        config = self.load_config()

        # Add the new server
        config["servers"][name] = {
            "url": url,
            "api_key": api_key,
            "default": set_default,
        }

        # Handle default server logic
        if set_default:
            # Unset default flag from all other servers
            for server_config in config["servers"].values():
                server_config["default"] = False
            config["servers"][name]["default"] = True
            config["default_server"] = name
        elif not config.get("default_server") and len(config["servers"]) == 1:
            # If this is the first server, make it default
            config["servers"][name]["default"] = True
            config["default_server"] = name

        self.save_config(config)

    def remove_server(self, name: str) -> bool:
        """
        Remove a server configuration.

        Returns True if server was found and removed.
        """
        config = self.load_config()

        if name not in config["servers"]:
            return False

        was_default = config["servers"][name].get("default", False)
        del config["servers"][name]

        # If we removed the default server, set a new default if servers remain
        if was_default:
            config["default_server"] = None
            if config["servers"]:
                # Set the first remaining server as default
                first_server = next(iter(config["servers"]))
                config["servers"][first_server]["default"] = True
                config["default_server"] = first_server

        self.save_config(config)
        return True

    def set_default_server(self, name: str) -> bool:
        """Set a server as the default. Returns True if successful."""
        config = self.load_config()

        if name not in config["servers"]:
            return False

        # Unset default flag from all servers
        for server_config in config["servers"].values():
            server_config["default"] = False

        # Set the specified server as default
        config["servers"][name]["default"] = True
        config["default_server"] = name

        self.save_config(config)
        return True

    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get all server configurations."""
        config = self.load_config()
        return cast("Dict[str, Dict[str, Any]]", config.get("servers", {}))
