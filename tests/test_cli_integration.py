"""
Integration tests for CLI commands using fixtures.

Tests the complete CLI command flow from command line invocation through
API calls using sanitized fixture data.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import responses
from click.testing import CliRunner

from ohc.cli import cli
from ohc.config import ConfigManager
from ohc.conversation_commands import conv
from ohc.server_commands import server


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def cli_with_commands(self):
        """Create CLI instance with commands registered."""
        # Register commands
        cli.add_command(server)
        cli.add_command(conv)
        return cli

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_config_manager(self, temp_config_dir):
        """Mock ConfigManager to use temporary directory."""
        with patch.object(
            ConfigManager, "_get_config_dir", return_value=temp_config_dir
        ):
            config_manager = ConfigManager()
            # Patch the ConfigManager class in all modules that use it
            with patch(
                "ohc.command_utils.ConfigManager", return_value=config_manager
            ), patch("ohc.server_commands.ConfigManager", return_value=config_manager):
                yield config_manager

    def test_cli_help(self, runner, cli_with_commands):
        """Test CLI help command."""
        result = runner.invoke(cli_with_commands, ["--help"])

        assert result.exit_code == 0
        assert "OpenHands Cloud CLI" in result.output
        assert "conv" in result.output
        assert "server" in result.output

    def test_cli_version(self, runner, cli_with_commands):
        """Test CLI version command."""
        result = runner.invoke(cli_with_commands, ["--version"])

        assert result.exit_code == 0
        assert "ohc, version" in result.output

    @responses.activate
    def test_server_list_empty(self, runner, cli_with_commands, mock_config_manager):
        """Test server list when no servers configured."""
        result = runner.invoke(cli_with_commands, ["server", "list"])

        assert result.exit_code == 0
        assert "No servers configured" in result.output

    def test_server_add_and_list(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test adding a server and listing it."""
        # Mock successful connection test
        fixture = fixture_loader.load("conversations_list_success")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search:
            mock_search.return_value = fixture["response"]["json"]

            # Add server non-interactively
            result = runner.invoke(
                cli_with_commands,
                [
                    "server",
                    "add",
                    "--name",
                    "test-server",
                    "--url",
                    "https://app.all-hands.dev/api/",
                    "--apikey",
                    "fake-api-key",
                    "--default",
                ],
            )

            assert result.exit_code == 0
            assert "Connection successful" in result.output
            assert "Server 'test-server' added" in result.output

        # List servers
        result = runner.invoke(cli_with_commands, ["server", "list"])

        assert result.exit_code == 0
        assert "test-server" in result.output
        assert "(default)" in result.output

    def test_server_test(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test server connection testing."""
        # First add a server
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock successful connection test
        fixture = fixture_loader.load("conversations_list_success")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search:
            mock_search.return_value = fixture["response"]["json"]

            result = runner.invoke(cli_with_commands, ["server", "test"])

            assert result.exit_code == 0
            assert "Connection successful" in result.output

    @responses.activate
    def test_conv_list_no_server(self, runner, cli_with_commands, mock_config_manager):
        """Test conversation list with no server configured."""
        result = runner.invoke(cli_with_commands, ["conv", "list"])

        assert result.exit_code == 0
        assert "No servers configured" in result.output

    def test_conv_list_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test successful conversation listing."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock API response
        fixture = fixture_loader.load("conversations_list_success")

        # Mock the OpenHandsAPI.search_conversations method
        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search:
            mock_search.return_value = fixture["response"]["json"]

            result = runner.invoke(cli_with_commands, ["conv", "list"])

            assert result.exit_code == 0
            assert "Found 2 conversations" in result.output
            assert "Example Conversation 1" in result.output
            assert "Example Conversation 2" in result.output

    def test_conv_list_with_limit(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test conversation listing with limit."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock API response
        fixture = fixture_loader.load("conversations_list_success")

        # Mock the OpenHandsAPI.search_conversations method
        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search:
            mock_search.return_value = fixture["response"]["json"]

            result = runner.invoke(cli_with_commands, ["conv", "list", "-n", "1"])

            assert result.exit_code == 0
            assert "Found 2 conversations" in result.output

    def test_conv_show_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test showing conversation details."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock conversation list for ID resolution
        list_fixture = fixture_loader.load("conversations_list_success")
        detail_fixture = fixture_loader.load("conversation_details")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search, patch(
            "ohc.api.OpenHandsAPI.get_conversation"
        ) as mock_get:
            mock_search.return_value = list_fixture["response"]["json"]
            mock_get.return_value = detail_fixture["response"]["json"]

            result = runner.invoke(
                cli_with_commands, ["conv", "show", "fake-uuid-12345678"]
            )

            assert result.exit_code == 0
            assert "Conversation Details" in result.output

    @responses.activate
    def test_conv_show_not_found(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test showing non-existent conversation."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock empty conversation list
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json={"conversations": [], "total": 0, "page_id": None, "has_more": False},
            status=200,
        )

        result = runner.invoke(cli_with_commands, ["conv", "show", "nonexistent"])

        assert result.exit_code == 0
        assert "No conversation found" in result.output

    def test_conv_wake_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test waking up a conversation."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock conversation list for ID resolution and conversation details
        list_fixture = fixture_loader.load("conversations_list_success")
        detail_fixture = fixture_loader.load("conversation_details")
        start_fixture = fixture_loader.load("conversation_start")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search, patch(
            "ohc.api.OpenHandsAPI.get_conversation"
        ) as mock_get, patch("ohc.api.OpenHandsAPI.start_conversation") as mock_start:
            mock_search.return_value = list_fixture["response"]["json"]
            mock_get.return_value = detail_fixture["response"]["json"]
            mock_start.return_value = start_fixture["response"]["json"]

            result = runner.invoke(
                cli_with_commands, ["conv", "wake", "fake-uuid-12345678"]
            )

            assert result.exit_code == 0
            assert "Conversation started successfully" in result.output

    def test_conv_ws_changes_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test showing workspace changes."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock conversation list for ID resolution, conversation details, and git changes
        list_fixture = fixture_loader.load("conversations_list_success")
        detail_fixture = fixture_loader.load("conversation_details")
        changes_fixture = fixture_loader.load("git_changes")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search, patch(
            "ohc.api.OpenHandsAPI.get_conversation"
        ) as mock_get, patch(
            "ohc.api.OpenHandsAPI.get_conversation_changes"
        ) as mock_changes:
            mock_search.return_value = list_fixture["response"]["json"]
            mock_get.return_value = detail_fixture["response"]["json"]
            mock_changes.return_value = changes_fixture["response"]["json"]

            result = runner.invoke(
                cli_with_commands, ["conv", "ws-changes", "fake-uuid-12345678"]
            )

            assert result.exit_code == 0
            assert "No changes found" in result.output

    def test_conv_ws_download_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test downloading workspace archive."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock conversation list for ID resolution and conversation details
        list_fixture = fixture_loader.load("conversations_list_success")
        detail_fixture = fixture_loader.load("conversation_details")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search, patch(
            "ohc.api.OpenHandsAPI.get_conversation"
        ) as mock_get, patch(
            "ohc.api.OpenHandsAPI.download_workspace_archive"
        ) as mock_download:
            mock_search.return_value = list_fixture["response"]["json"]
            mock_get.return_value = detail_fixture["response"]["json"]
            mock_download.return_value = b"fake-zip-content"

            with tempfile.TemporaryDirectory() as temp_dir:
                result = runner.invoke(
                    cli_with_commands,
                    [
                        "conv",
                        "ws-download",
                        "fake-uuid-12345678",
                        "-o",
                        f"{temp_dir}/test.zip",
                    ],
                )

                assert result.exit_code == 0
                assert "Workspace downloaded" in result.output
                assert Path(f"{temp_dir}/test.zip").exists()

    def test_conv_trajectory_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test downloading conversation trajectory."""
        # Add server configuration
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Mock conversation list for ID resolution, conversation details, and trajectory
        list_fixture = fixture_loader.load("conversations_list_success")
        detail_fixture = fixture_loader.load("conversation_details")
        trajectory_fixture = fixture_loader.load("trajectory")

        with patch("ohc.api.OpenHandsAPI.search_conversations") as mock_search, patch(
            "ohc.api.OpenHandsAPI.get_conversation"
        ) as mock_get, patch("ohc.api.OpenHandsAPI.get_trajectory") as mock_trajectory:
            mock_search.return_value = list_fixture["response"]["json"]
            mock_get.return_value = detail_fixture["response"]["json"]
            mock_trajectory.return_value = trajectory_fixture["response"]["json"]

            result = runner.invoke(
                cli_with_commands, ["conv", "trajectory", "fake-uuid-12345678"]
            )

            assert result.exit_code == 0
            assert "Trajectory for:" in result.output

    def test_interactive_mode_no_server(
        self, runner, cli_with_commands, mock_config_manager
    ):
        """Test interactive mode with no server configured."""
        result = runner.invoke(
            cli_with_commands, ["-i"], input="\n"
        )  # Provide empty input (default "N")

        assert result.exit_code == 0
        assert "No servers configured" in result.output
        assert "Would you like to add a server now?" in result.output

    @responses.activate
    def test_server_delete_success(
        self, runner, cli_with_commands, mock_config_manager, fixture_loader
    ):
        """Test deleting a server configuration."""
        # Add server first
        config_manager = mock_config_manager
        config_manager.add_server(
            "test-server",
            "https://app.all-hands.dev/api/",
            "fake-api-key",
            set_default=True,
        )

        # Delete with force flag
        result = runner.invoke(
            cli_with_commands, ["server", "delete", "test-server", "--force"]
        )

        assert result.exit_code == 0
        assert "Server 'test-server' deleted" in result.output

        # Verify it's gone
        result = runner.invoke(cli_with_commands, ["server", "list"])
        assert "No servers configured" in result.output

    @responses.activate
    def test_server_set_default(self, runner, cli_with_commands, mock_config_manager):
        """Test setting a server as default."""
        # Add two servers
        config_manager = mock_config_manager
        config_manager.add_server(
            "server1", "https://app.all-hands.dev/api/", "key1", set_default=True
        )
        config_manager.add_server(
            "server2", "https://app.all-hands.dev/api/", "key2", set_default=False
        )

        # Set server2 as default
        result = runner.invoke(cli_with_commands, ["server", "set-default", "server2"])

        assert result.exit_code == 0
        assert "Server 'server2' set as default" in result.output

        # Verify the change
        result = runner.invoke(cli_with_commands, ["server", "list"])
        assert "server2" in result.output
        assert "(default)" in result.output
