"""
Tests for server management commands.

Tests the ohc.server_commands module including:
- Server addition with validation
- Server listing and display
- Server deletion with confirmation
- Default server management
- Connection testing
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from ohc.server_commands import add, delete, list, server, set_default, test


class TestServerCommands:
    """Test server management commands."""

    def test_server_group(self):
        """Test server command group."""
        runner = CliRunner()
        result = runner.invoke(server, ["--help"])

        assert result.exit_code == 0
        assert "Manage OpenHands server configurations" in result.output

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_with_options(self, mock_api_class, mock_config_class):
        """Test adding server with all options provided."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.return_value = {"results": []}
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(
            add,
            [
                "--name",
                "test-server",
                "--url",
                "https://test.com/api/",
                "--apikey",
                "test-key",
                "--default",
            ],
        )

        assert result.exit_code == 0
        assert "✓ Connection successful" in result.output
        assert "✓ Server 'test-server' added and set as default" in result.output

        # Verify API calls
        mock_api.test_connection.assert_called_once()
        mock_api.search_conversations.assert_called_once_with(limit=1)
        mock_config.add_server.assert_called_once_with(
            "test-server", "https://test.com/api/", "test-key", True
        )

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_with_prompts(self, mock_api_class, mock_config_class):
        """Test adding server with interactive prompts."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.return_value = {"results": []}
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(
            add, input="test-server\nhttps://test.com/\ntest-key\ny\n"
        )

        assert result.exit_code == 0
        assert "Server name:" in result.output
        assert "Server URL" in result.output  # May have default in brackets
        assert "API Key:" in result.output
        assert "Set as default server?" in result.output

        # Verify URL normalization
        mock_config.add_server.assert_called_once_with(
            "test-server", "https://test.com/api/", "test-key", True
        )

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_url_normalization(self, mock_api_class, mock_config_class):
        """Test URL normalization during server addition."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.return_value = {"results": []}
        mock_api_class.return_value = mock_api

        runner = CliRunner()

        # Test URL without trailing slash
        result = runner.invoke(
            add,
            ["--name", "test1", "--url", "https://test.com", "--apikey", "key1"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_config.add_server.assert_called_with(
            "test1", "https://test.com/api/", "key1", False
        )

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_connection_failure(self, mock_api_class, mock_config_class):
        """Test adding server with connection failure."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = False
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(
            add,
            [
                "--name",
                "test-server",
                "--url",
                "https://invalid.com/api/",
                "--apikey",
                "invalid-key",
            ],
            input="n\ny\n",
        )  # Don't set as default, then save anyway

        assert result.exit_code == 0
        assert "✗ Connection test failed" in result.output
        assert "Save server configuration anyway?" in result.output
        mock_config.add_server.assert_called_once()

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_connection_exception(self, mock_api_class, mock_config_class):
        """Test adding server with connection exception."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.side_effect = Exception("Network error")
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(
            add,
            [
                "--name",
                "test-server",
                "--url",
                "https://test.com/api/",
                "--apikey",
                "test-key",
            ],
            input="n\n",
        )  # Don't save

        assert result.exit_code == 1  # Should abort
        assert "✗ Connection failed: Network error" in result.output

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_existing_overwrite(self, mock_api_class, mock_config_class):
        """Test adding server that already exists with overwrite."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.return_value = {"results": []}
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(
            add,
            [
                "--name",
                "test-server",
                "--url",
                "https://test.com/api/",
                "--apikey",
                "test-key",
            ],
            input="n\ny\n",
        )  # Don't set as default, then overwrite existing

        assert result.exit_code == 0
        assert "Server 'test-server' already exists. Overwrite?" in result.output
        assert "✓ Server 'test-server' added" in result.output
        mock_config.add_server.assert_called_once_with(
            "test-server", "https://test.com/api/", "test-key", False
        )

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_existing_cancel(self, mock_api_class, mock_config_class):
        """Test adding server that already exists with cancel."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config_class.return_value = mock_config

        # Don't need API mocks since we won't reach connection testing

        runner = CliRunner()
        result = runner.invoke(
            add,
            [
                "--name",
                "test-server",
                "--url",
                "https://test.com/api/",
                "--apikey",
                "test-key",
            ],
            input="n\nn\n",
        )  # Don't set as default, then don't overwrite

        assert result.exit_code == 0
        assert "Operation cancelled." in result.output
        mock_config.add_server.assert_not_called()

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_add_server_limited_permissions(self, mock_api_class, mock_config_class):
        """Test adding server with limited API permissions."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.side_effect = Exception("Permission denied")
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(
            add,
            [
                "--name",
                "test-server",
                "--url",
                "https://test.com/api/",
                "--apikey",
                "limited-key",
            ],
            input="n\ny\n",
        )  # Don't set as default, then save anyway

        assert result.exit_code == 0
        assert "⚠ Connection partially successful" in result.output
        assert "API key may have limited permissions" in result.output
        mock_config.add_server.assert_called_once_with(
            "test-server", "https://test.com/api/", "limited-key", False
        )

    @patch("ohc.server_commands.ConfigManager")
    def test_list_servers_empty(self, mock_config_class):
        """Test listing servers when none are configured."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(list)

        assert result.exit_code == 0
        assert "No servers configured." in result.output
        assert "Use 'ohc server add' to add a server." in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_list_servers_with_data(self, mock_config_class):
        """Test listing servers with configured servers."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {
            "server1": {"url": "https://server1.com/api/", "default": True},
            "server2": {"url": "https://server2.com/api/", "default": False},
            "server3": {"url": "https://server3.com/api/"},  # No default key
        }
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(list)

        assert result.exit_code == 0
        assert "Configured servers:" in result.output
        assert "* server1" in result.output  # Default marker
        assert "(default)" in result.output
        assert "  server2" in result.output  # No default marker
        assert "  server3" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_delete_server_success(self, mock_config_class):
        """Test successful server deletion."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.remove_server.return_value = True
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(delete, ["test-server"], input="y\n")

        assert result.exit_code == 0
        assert "Delete server 'test-server'?" in result.output
        assert "✓ Server 'test-server' deleted" in result.output
        mock_config.remove_server.assert_called_once_with("test-server")

    @patch("ohc.server_commands.ConfigManager")
    def test_delete_server_force(self, mock_config_class):
        """Test server deletion with force flag."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.remove_server.return_value = True
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(delete, ["test-server", "--force"])

        assert result.exit_code == 0
        assert "Delete server 'test-server'?" not in result.output  # No confirmation
        assert "✓ Server 'test-server' deleted" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_delete_server_not_found(self, mock_config_class):
        """Test deleting non-existent server."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(delete, ["nonexistent"])

        assert result.exit_code == 0
        assert "✗ Server 'nonexistent' not found." in result.output
        mock_config.remove_server.assert_not_called()

    @patch("ohc.server_commands.ConfigManager")
    def test_delete_server_cancelled(self, mock_config_class):
        """Test server deletion cancelled by user."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(delete, ["test-server"], input="n\n")

        assert result.exit_code == 0
        assert "Operation cancelled." in result.output
        mock_config.remove_server.assert_not_called()

    @patch("ohc.server_commands.ConfigManager")
    def test_delete_server_failure(self, mock_config_class):
        """Test server deletion failure."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.remove_server.return_value = False
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(delete, ["test-server"], input="y\n")

        assert result.exit_code == 0
        assert "✗ Failed to delete server 'test-server'" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_delete_server_exception(self, mock_config_class):
        """Test server deletion with exception."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.remove_server.side_effect = Exception("Delete error")
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(delete, ["test-server"], input="y\n")

        assert result.exit_code == 0
        assert "✗ Failed to delete server: Delete error" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_set_default_success(self, mock_config_class):
        """Test setting default server successfully."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.set_default_server.return_value = True
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(set_default, ["test-server"])

        assert result.exit_code == 0
        assert "✓ Server 'test-server' set as default" in result.output
        mock_config.set_default_server.assert_called_once_with("test-server")

    @patch("ohc.server_commands.ConfigManager")
    def test_set_default_not_found(self, mock_config_class):
        """Test setting default for non-existent server."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {}
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(set_default, ["nonexistent"])

        assert result.exit_code == 0
        assert "✗ Server 'nonexistent' not found." in result.output
        mock_config.set_default_server.assert_not_called()

    @patch("ohc.server_commands.ConfigManager")
    def test_set_default_failure(self, mock_config_class):
        """Test setting default server failure."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.set_default_server.return_value = False
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(set_default, ["test-server"])

        assert result.exit_code == 0
        assert "✗ Failed to set server 'test-server' as default" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_set_default_exception(self, mock_config_class):
        """Test setting default server with exception."""
        mock_config = MagicMock()
        mock_config.list_servers.return_value = {"test-server": {}}
        mock_config.set_default_server.side_effect = Exception("Set default error")
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(set_default, ["test-server"])

        assert result.exit_code == 0
        assert "✗ Failed to set default server: Set default error" in result.output

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_test_server_success(self, mock_api_class, mock_config_class):
        """Test server connection test success."""
        mock_config = MagicMock()
        mock_config.get_server_config.return_value = {
            "api_key": "test-key",
            "url": "https://test.com/api/",
        }
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.return_value = {"results": []}
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(test, ["test-server"])

        assert result.exit_code == 0
        assert "Testing connection to server 'test-server'..." in result.output
        assert "✓ Connection successful" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_test_server_not_found(self, mock_config_class):
        """Test server connection test for non-existent server."""
        mock_config = MagicMock()
        mock_config.get_server_config.return_value = None
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(test, ["nonexistent"])

        assert result.exit_code == 0
        assert "✗ Server 'nonexistent' not found." in result.output

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_test_server_connection_failure(self, mock_api_class, mock_config_class):
        """Test server connection test failure."""
        mock_config = MagicMock()
        mock_config.get_server_config.return_value = {
            "api_key": "test-key",
            "url": "https://test.com/api/",
        }
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = False
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(test, ["test-server"])

        assert result.exit_code == 0
        assert "✗ Connection test failed" in result.output

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_test_server_exception(self, mock_api_class, mock_config_class):
        """Test server connection test with exception."""
        mock_config = MagicMock()
        mock_config.get_server_config.return_value = {
            "api_key": "test-key",
            "url": "https://test.com/api/",
        }
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.side_effect = Exception("Connection error")
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(test, ["test-server"])

        assert result.exit_code == 0
        assert "✗ Connection failed: Connection error" in result.output

    @patch("ohc.server_commands.ConfigManager")
    def test_test_default_server_no_servers(self, mock_config_class):
        """Test testing default server when none configured."""
        mock_config = MagicMock()
        mock_config.get_server_config.return_value = None
        mock_config_class.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(test, [])

        assert result.exit_code == 0
        assert "✗ No servers configured." in result.output

    @patch("ohc.server_commands.ConfigManager")
    @patch("ohc.server_commands.OpenHandsAPI")
    def test_test_default_server_success(self, mock_api_class, mock_config_class):
        """Test testing default server successfully."""
        mock_config = MagicMock()
        mock_config.get_server_config.return_value = {
            "api_key": "test-key",
            "url": "https://test.com/api/",
        }
        mock_config.list_servers.return_value = {
            "default-server": {"api_key": "test-key", "url": "https://test.com/api/"}
        }
        mock_config_class.return_value = mock_config

        mock_api = MagicMock()
        mock_api.test_connection.return_value = True
        mock_api.search_conversations.return_value = {"results": []}
        mock_api_class.return_value = mock_api

        runner = CliRunner()
        result = runner.invoke(test, [])

        assert result.exit_code == 0
        assert "Testing connection to server 'default-server'..." in result.output
        assert "✓ Connection successful" in result.output
