"""Tests for conversation commands CLI functionality."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import responses
from click.testing import CliRunner

from ohc.conversation_commands import conv


class TestConversationCommandsCLI:
    """Test CLI functionality of conversation commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_config = {"api_key": "test-api-key", "url": "https://api.test.com"}

    def _load_and_fix_conversations_fixture(self, fixture_name: str):
        """Load VCR fixture and transform it for API mocking."""
        fixture_path = Path(__file__).parent / "fixtures" / "sanitized" / fixture_name
        with open(fixture_path) as f:
            vcr_data = json.load(f)
            fixture_data = vcr_data["response"]["json"]

        # The fixture already has the correct format with "results"
        return fixture_data

    def _load_conversation_detail_fixture(self, fixture_name: str):
        """Load conversation detail fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "sanitized" / fixture_name
        with open(fixture_path) as f:
            vcr_data = json.load(f)
            return vcr_data["response"]["json"]

    @responses.activate
    def test_list_command_success(self):
        """Test list command with successful API response."""
        fixed_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=fixed_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["list"])

            assert result.exit_code == 0
            assert "Found 2 conversations:" in result.output
            assert "fake-uui" in result.output  # ID is truncated to 8 chars
            assert "Example Conversation 1" in result.output

    @responses.activate
    def test_list_command_empty_results(self):
        """Test list command with no conversations."""
        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json={"results": []},
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["list"])

            assert result.exit_code == 0
            assert "No conversations found." in result.output

    @responses.activate
    def test_list_command_long_title(self):
        """Test list command with conversation that has a very long title."""
        long_title = "A" * 100  # Title longer than 50 chars
        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json={
                "results": [
                    {
                        "conversation_id": "test-id-123",
                        "title": long_title,
                        "status": "RUNNING",
                    }
                ]
            },
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["list"])

            assert result.exit_code == 0
            # Title should be truncated with "..."
            assert "A" * 47 + "..." in result.output

    @responses.activate
    def test_show_command_success(self):
        """Test show command with successful API response."""
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )
        detail_data = self._load_conversation_detail_fixture(
            "conversation_details.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["show", "1"])

            assert result.exit_code == 0
            assert "Example Conversation" in result.output

    def test_list_command_no_server_config(self):
        """Test list command with no server configuration."""
        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = None

            result = self.runner.invoke(conv, ["list"])

            assert result.exit_code == 0
            assert "No servers configured" in result.output

    def test_show_command_invalid_server(self):
        """Test show command with invalid server name."""
        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = None

            result = self.runner.invoke(conv, ["show", "1", "--server", "invalid"])

            assert result.exit_code == 0
            assert "Server 'invalid' not found" in result.output

    @responses.activate
    def test_wake_command_success(self):
        """Test wake command with successful API response."""
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )
        detail_data = self._load_conversation_detail_fixture(
            "conversation_details.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://api.test.com/conversations/fake-uuid-12345678/start",
            json={"url": "https://runtime.test.com/conversation/fake-uuid-12345678"},
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["wake", "1"])

            assert result.exit_code == 0
            assert "Waking up conversation" in result.output
            assert "Conversation started successfully" in result.output

    @responses.activate
    def test_conversation_id_resolution_by_partial_id(self):
        """Test conversation ID resolution using partial ID."""
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )
        detail_data = self._load_conversation_detail_fixture(
            "conversation_details.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["show", "fake-uuid-1"])

            assert result.exit_code == 0
            assert "Example Conversation" in result.output

    @responses.activate
    def test_conversation_id_resolution_no_match(self):
        """Test conversation ID resolution with no matching conversations."""
        # Load fixture data
        list_fixture = (
            Path(__file__).parent
            / "fixtures"
            / "sanitized"
            / "conversations_list_success.json"
        )

        with open(list_fixture) as f:
            list_data = json.load(f)

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["show", "nonexist"])

            assert result.exit_code == 0
            assert (
                "No conversation found with ID starting with 'nonexist'"
                in result.output
            )

    @responses.activate
    def test_conversation_number_out_of_range(self):
        """Test conversation number that's out of range."""
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            result = self.runner.invoke(conv, ["show", "99"])

            assert result.exit_code == 0
            assert "Conversation number 99 is out of range (1-2)" in result.output

    def test_api_error_handling(self):
        """Test error handling when API calls fail."""
        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            with patch("ohc.command_utils.OpenHandsAPI") as mock_api_class:
                mock_api = Mock()
                mock_api.search_conversations.side_effect = Exception("API Error")
                mock_api_class.return_value = mock_api

                result = self.runner.invoke(conv, ["list"])

                assert result.exit_code == 0
                assert "Failed to list conversations: API Error" in result.output

    def test_interactive_mode_no_server_config(self):
        """Test interactive mode when no server is configured."""
        with patch(
            "ohc.conversation_commands.ConfigManager"
        ) as mock_config_manager_class:
            mock_config_manager = MagicMock()
            mock_config_manager.get_server_config.return_value = None
            mock_config_manager_class.return_value = mock_config_manager

            with patch("click.confirm", return_value=False):
                with patch("click.echo") as mock_echo:
                    from ohc.conversation_commands import interactive_mode

                    interactive_mode()

                    mock_echo.assert_any_call("No servers configured.")
                    mock_echo.assert_any_call(
                        "Use 'ohc server add' to add a server configuration."
                    )

    def test_interactive_mode_add_server_accepted(self):
        """Test interactive mode when user accepts to add server."""
        with patch(
            "ohc.conversation_commands.ConfigManager"
        ) as mock_config_manager_class:
            mock_config_manager = MagicMock()
            # First call returns None, second call returns config after adding server
            mock_config_manager.get_server_config.side_effect = [
                None,
                {"name": "test", "url": "https://api.test.com", "api_key": "key"},
            ]
            mock_config_manager_class.return_value = mock_config_manager

            with patch("click.confirm", return_value=True):
                with patch("click.Context") as mock_context_class:
                    mock_context = MagicMock()
                    mock_context_class.return_value = mock_context

                    with patch(
                        "conversation_manager.conversation_manager.ConversationManager"
                    ) as mock_manager_class:
                        mock_manager = MagicMock()
                        mock_manager_class.return_value = mock_manager

                        from ohc.conversation_commands import interactive_mode

                        interactive_mode()

                        mock_manager.run_interactive.assert_called_once()

    def test_interactive_mode_success(self):
        """Test successful interactive mode launch."""
        with patch(
            "ohc.conversation_commands.ConfigManager"
        ) as mock_config_manager_class:
            mock_config_manager = MagicMock()
            mock_config_manager.get_server_config.return_value = {
                "name": "test-server",
                "url": "https://api.test.com",
                "api_key": "test-key",
            }
            mock_config_manager_class.return_value = mock_config_manager

            with patch(
                "conversation_manager.conversation_manager.ConversationManager"
            ) as mock_manager_class:
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager

                from ohc.conversation_commands import interactive_mode

                interactive_mode()

                mock_manager.run_interactive.assert_called_once()

    def test_interactive_mode_exception(self):
        """Test interactive mode with exception."""
        with patch(
            "ohc.conversation_commands.ConfigManager"
        ) as mock_config_manager_class:
            mock_config_manager_class.side_effect = Exception("Config error")

            with patch("click.echo") as mock_echo:
                with patch("sys.exit") as mock_exit:
                    from ohc.conversation_commands import interactive_mode

                    interactive_mode()

                    mock_echo.assert_any_call(
                        "✗ Failed to start interactive mode: Config error", err=True
                    )
                    mock_exit.assert_called_with(1)

    @responses.activate
    def test_download_command_success(self):
        """Test successful workspace download."""
        # Mock conversation list for ID resolution
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )

        # Mock conversation details
        detail_data = {
            "id": "fake-uuid-12345678",
            "title": "Test Conversation",
            "url": "https://runtime.test.com/conversation/fake-uuid-12345678",
            "session_api_key": "session-key-123",
        }

        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200,
        )

        # Mock workspace archive download
        archive_data = b"fake zip content"
        responses.add(
            responses.GET,
            "https://runtime.test.com/api/conversations/fake-uuid-12345678/zip-directory",
            body=archive_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            with patch("builtins.open", mock_open()) as mock_file:
                result = self.runner.invoke(conv, ["ws-download", "fake-uuid-12345678"])

                assert result.exit_code == 0
                assert "Downloading workspace for: Test Conversation" in result.output
                assert "Workspace downloaded successfully" in result.output
                mock_file.assert_called_once_with("fake-uui.zip", "wb")

    @responses.activate
    def test_download_command_with_output_file(self):
        """Test workspace download with custom output filename."""
        # Mock conversation list for ID resolution
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )

        detail_data = {
            "id": "fake-uuid-12345678",
            "title": "Test Conversation",
            "url": "https://runtime.test.com/conversation/fake-uuid-12345678",
            "session_api_key": "session-key-123",
        }

        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200,
        )

        archive_data = b"fake zip content"
        responses.add(
            responses.GET,
            "https://runtime.test.com/api/conversations/fake-uuid-12345678/zip-directory",
            body=archive_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            with patch("builtins.open", mock_open()) as mock_file:
                result = self.runner.invoke(
                    conv, ["ws-download", "fake-uuid-12345678", "-o", "custom.zip"]
                )

                assert result.exit_code == 0
                assert "Workspace downloaded successfully: custom.zip" in result.output
                mock_file.assert_called_once_with("custom.zip", "wb")

    @responses.activate
    def test_download_command_error(self):
        """Test workspace download with error."""
        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            with patch("ohc.command_utils.OpenHandsAPI") as mock_api_class:
                mock_api = Mock()
                mock_api.search_conversations.side_effect = Exception("Download error")
                mock_api_class.return_value = mock_api

                result = self.runner.invoke(conv, ["ws-download", "fake-uuid-12345678"])

                assert result.exit_code == 0
                assert "Failed to download workspace: Download error" in result.output

    @responses.activate
    def test_changes_command_success(self):
        """Test successful workspace changes display."""
        list_data = self._load_and_fix_conversations_fixture(
            "conversations_list_success.json"
        )

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200,
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = (
                self.mock_config
            )

            with patch(
                "ohc.conversation_commands.show_workspace_changes"
            ) as mock_show_changes:
                result = self.runner.invoke(conv, ["ws-changes", "1"])

                assert result.exit_code == 0
                mock_show_changes.assert_called_once()
