"""
Tests for configuration management functionality.

Tests the ConfigManager class including:
- XDG Base Directory Specification compliance
- Configuration file loading and saving
- Server CRUD operations
- Default server management
- Error handling and edge cases
"""

import json
import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ohc.config import ConfigManager


class TestConfigManager:
    """Test configuration management functionality."""

    def test_config_dir_xdg_config_home(self):
        """Test config directory uses XDG_CONFIG_HOME when set."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"}):
            with patch("pathlib.Path.mkdir"):
                config_manager = ConfigManager()

                assert config_manager.config_dir == Path("/custom/config/ohc")

    def test_config_dir_default_location(self):
        """Test config directory uses default location when XDG_CONFIG_HOME not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.home") as mock_home:
                with patch("pathlib.Path.mkdir"):
                    mock_home.return_value = Path("/home/user")
                    config_manager = ConfigManager()

                    assert config_manager.config_dir == Path("/home/user/.config/ohc")

    def test_load_config_file_not_exists(self):
        """Test loading config when file doesn't exist returns default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config = config_manager.load_config()

            assert config == {"servers": {}, "default_server": None}

    def test_load_config_valid_file(self):
        """Test loading valid configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            test_config = {
                "servers": {
                    "test-server": {
                        "url": "https://api.example.com",
                        "api_key": "test-key",
                        "default": True,
                    }
                },
                "default_server": "test-server",
            }

            with open(config_manager.config_file, "w") as f:
                json.dump(test_config, f)

            config = config_manager.load_config()

            assert config == test_config

    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON raises exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            with open(config_manager.config_file, "w") as f:
                f.write("invalid json content")

            with pytest.raises(Exception, match="Failed to load configuration"):
                config_manager.load_config()

    def test_save_config_creates_file(self):
        """Test saving configuration creates file with correct content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            test_config = {
                "servers": {"test": {"url": "https://api.test.com", "api_key": "key"}},
                "default_server": "test",
            }

            config_manager.save_config(test_config)

            assert config_manager.config_file.exists()

            with open(config_manager.config_file) as f:
                saved_config = json.load(f)

            assert saved_config == test_config

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix file permissions not supported on Windows",
    )
    def test_save_config_sets_permissions(self):
        """Test saving config sets restrictive file permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config_manager.save_config({"servers": {}, "default_server": None})

            # Check file permissions (0o600 = owner read/write only)
            file_mode = config_manager.config_file.stat().st_mode & 0o777
            assert file_mode == 0o600

    def test_get_server_config_by_name(self):
        """Test getting server config by specific name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            test_config = {
                "servers": {
                    "server1": {"url": "https://api1.com", "api_key": "key1"},
                    "server2": {"url": "https://api2.com", "api_key": "key2"},
                },
                "default_server": "server1",
            }

            config_manager.save_config(test_config)

            server_config = config_manager.get_server_config("server2")

            assert server_config == {"url": "https://api2.com", "api_key": "key2"}

    def test_get_server_config_default_server(self):
        """Test getting default server config when no name specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            test_config = {
                "servers": {
                    "server1": {"url": "https://api1.com", "api_key": "key1"},
                    "server2": {"url": "https://api2.com", "api_key": "key2"},
                },
                "default_server": "server2",
            }

            config_manager.save_config(test_config)

            server_config = config_manager.get_server_config()

            assert server_config == {"url": "https://api2.com", "api_key": "key2"}

    def test_get_server_config_first_server_fallback(self):
        """Test getting first server when no default set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            test_config = {
                "servers": {"server1": {"url": "https://api1.com", "api_key": "key1"}},
                "default_server": None,
            }

            config_manager.save_config(test_config)

            server_config = config_manager.get_server_config()

            assert server_config == {"url": "https://api1.com", "api_key": "key1"}

    def test_get_server_config_not_found(self):
        """Test getting non-existent server returns None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            server_config = config_manager.get_server_config("nonexistent")

            assert server_config is None

    def test_add_server_first_server(self):
        """Test adding first server sets it as default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config_manager.add_server("test-server", "https://api.test.com", "test-key")

            config = config_manager.load_config()

            assert config["servers"]["test-server"]["url"] == "https://api.test.com"
            assert config["servers"]["test-server"]["api_key"] == "test-key"
            assert config["servers"]["test-server"]["default"] is True
            assert config["default_server"] == "test-server"

    def test_add_server_set_default_true(self):
        """Test adding server with set_default=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            # Add first server
            config_manager.add_server("server1", "https://api1.com", "key1")

            # Add second server as default
            config_manager.add_server(
                "server2", "https://api2.com", "key2", set_default=True
            )

            config = config_manager.load_config()

            assert config["servers"]["server1"]["default"] is False
            assert config["servers"]["server2"]["default"] is True
            assert config["default_server"] == "server2"

    def test_add_server_set_default_false(self):
        """Test adding server with set_default=False keeps existing default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            # Add first server (becomes default)
            config_manager.add_server("server1", "https://api1.com", "key1")

            # Add second server without setting as default
            config_manager.add_server(
                "server2", "https://api2.com", "key2", set_default=False
            )

            config = config_manager.load_config()

            assert config["servers"]["server1"]["default"] is True
            assert config["servers"]["server2"]["default"] is False
            assert config["default_server"] == "server1"

    def test_remove_server_exists(self):
        """Test removing existing server returns True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config_manager.add_server("test-server", "https://api.test.com", "test-key")

            result = config_manager.remove_server("test-server")

            assert result is True

            config = config_manager.load_config()
            assert "test-server" not in config["servers"]

    def test_remove_server_not_exists(self):
        """Test removing non-existent server returns False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            result = config_manager.remove_server("nonexistent")

            assert result is False

    def test_remove_default_server_sets_new_default(self):
        """Test removing default server sets new default from remaining servers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            # Add two servers
            config_manager.add_server("server1", "https://api1.com", "key1")
            config_manager.add_server("server2", "https://api2.com", "key2")

            # Remove the default server (server1)
            config_manager.remove_server("server1")

            config = config_manager.load_config()

            assert "server1" not in config["servers"]
            assert config["servers"]["server2"]["default"] is True
            assert config["default_server"] == "server2"

    def test_remove_last_server_clears_default(self):
        """Test removing last server clears default_server."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config_manager.add_server("test-server", "https://api.test.com", "test-key")
            config_manager.remove_server("test-server")

            config = config_manager.load_config()

            assert config["servers"] == {}
            assert config["default_server"] is None

    def test_set_default_server_exists(self):
        """Test setting existing server as default returns True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config_manager.add_server("server1", "https://api1.com", "key1")
            config_manager.add_server("server2", "https://api2.com", "key2")

            result = config_manager.set_default_server("server2")

            assert result is True

            config = config_manager.load_config()
            assert config["servers"]["server1"]["default"] is False
            assert config["servers"]["server2"]["default"] is True
            assert config["default_server"] == "server2"

    def test_set_default_server_not_exists(self):
        """Test setting non-existent server as default returns False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            result = config_manager.set_default_server("nonexistent")

            assert result is False

    def test_list_servers_empty(self):
        """Test listing servers when none configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            servers = config_manager.list_servers()

            assert servers == {}

    def test_list_servers_multiple(self):
        """Test listing multiple configured servers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            config_manager.add_server("server1", "https://api1.com", "key1")
            config_manager.add_server("server2", "https://api2.com", "key2")

            servers = config_manager.list_servers()

            assert len(servers) == 2
            assert "server1" in servers
            assert "server2" in servers
            assert servers["server1"]["url"] == "https://api1.com"
            assert servers["server2"]["url"] == "https://api2.com"

    def test_save_config_os_error(self):
        """Test save_config with OSError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir)
            config_manager.config_file = config_manager.config_dir / "config.json"

            # Mock os.chmod to raise OSError
            with patch("os.chmod", side_effect=OSError("Permission denied")):
                with pytest.raises(Exception, match="Failed to save configuration"):
                    config_manager.add_server("test", "https://api.test.com", "key")
