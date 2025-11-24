"""
Configuration management for OpenHands Cloud CLI.

Handles server configuration storage and retrieval following XDG Base Directory Specification.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any


class ConfigManager:
    """Manages OpenHands Cloud CLI configuration."""
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_config_dir(self) -> Path:
        """Get configuration directory following XDG Base Directory Specification."""
        xdg_config = os.getenv('XDG_CONFIG_HOME')
        if xdg_config:
            return Path(xdg_config) / 'ohc'
        return Path.home() / '.config' / 'ohc'
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_file.exists():
            return {
                "servers": {},
                "default_server": None
            }
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise Exception(f"Failed to load configuration: {e}")
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file with secure permissions."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            # Set restrictive permissions for security
            os.chmod(self.config_file, 0o600)
        except IOError as e:
            raise Exception(f"Failed to save configuration: {e}")
    
    def get_server_config(self, server_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server or the default server."""
        config = self.load_config()
        
        if server_name:
            return config["servers"].get(server_name)
        
        # Return default server if no specific server requested
        default_server = config.get("default_server")
        if default_server and default_server in config["servers"]:
            return config["servers"][default_server]
        
        # If no default set, return the first server if any exist
        if config["servers"]:
            return next(iter(config["servers"].values()))
        
        return None
    
    def add_server(self, name: str, url: str, api_key: str, set_default: bool = False) -> None:
        """Add a new server configuration."""
        config = self.load_config()
        
        # Add the new server
        config["servers"][name] = {
            "url": url,
            "api_key": api_key,
            "default": set_default
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
        """Remove a server configuration. Returns True if server was found and removed."""
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
        return config.get("servers", {})