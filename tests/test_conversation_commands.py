"""Tests for conversation commands CLI functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import responses
from click.testing import CliRunner

from ohc.conversation_commands import conv


class TestConversationCommandsCLI:
    """Test CLI functionality of conversation commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_config = {
            "api_key": "test-api-key",
            "url": "https://api.test.com"
        }

    def _load_and_fix_conversations_fixture(self, fixture_name: str):
        """Load VCR fixture and transform it for API mocking."""
        fixture_path = Path(__file__).parent / "fixtures" / "sanitized" / fixture_name
        with open(fixture_path) as f:
            vcr_data = json.load(f)
            fixture_data = vcr_data["response"]["json"]

        # Transform fixture data to match what the command expects
        conversations = []
        for conversation in fixture_data["conversations"]:
            conversations.append({
                "conversation_id": conversation["id"],  # Command expects 'conversation_id'
                "title": conversation["title"],
                "status": "STOPPED",  # Add status field that command expects
                "created_at": conversation["created_at"],
                "updated_at": conversation["updated_at"]
            })

        return {
            "results": conversations,  # Command expects 'results' not 'conversations'
            "total": fixture_data["total"],
            "page_id": fixture_data["page_id"],
            "has_more": fixture_data["has_more"]
        }

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
            status=200
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

            result = self.runner.invoke(conv, ["list"])

            assert result.exit_code == 0
            assert "Found 2 conversations:" in result.output
            assert "fake-uui" in result.output  # ID is truncated to 8 chars
            assert "Example Conversation 1" in result.output

    @responses.activate
    def test_show_command_success(self):
        """Test show command with successful API response."""
        list_data = self._load_and_fix_conversations_fixture("conversations_list_success.json")
        detail_data = self._load_conversation_detail_fixture("conversation_details.json")

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

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
        list_data = self._load_and_fix_conversations_fixture("conversations_list_success.json")
        detail_data = self._load_conversation_detail_fixture("conversation_details.json")

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.test.com/conversations/fake-uuid-12345678/start",
            json={"url": "https://runtime.test.com/conversation/fake-uuid-12345678"},
            status=200
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

            result = self.runner.invoke(conv, ["wake", "1"])

            assert result.exit_code == 0
            assert "Waking up conversation" in result.output
            assert "Conversation started successfully" in result.output

    @responses.activate
    def test_conversation_id_resolution_by_partial_id(self):
        """Test conversation ID resolution using partial ID."""
        list_data = self._load_and_fix_conversations_fixture("conversations_list_success.json")
        detail_data = self._load_conversation_detail_fixture("conversation_details.json")

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.test.com/conversations/fake-uuid-12345678",
            json=detail_data,
            status=200
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

            result = self.runner.invoke(conv, ["show", "fake-uuid-1"])

            assert result.exit_code == 0
            assert "Example Conversation" in result.output

    @responses.activate
    def test_conversation_id_resolution_no_match(self):
        """Test conversation ID resolution with no matching conversations."""
        # Load fixture data
        list_fixture = Path(__file__).parent / "fixtures" / "sanitized" / "conversations_list_success.json"

        with open(list_fixture) as f:
            list_data = json.load(f)

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

            result = self.runner.invoke(conv, ["show", "nonexist"])

            assert result.exit_code == 0
            assert "No conversation found with ID starting with 'nonexist'" in result.output

    @responses.activate
    def test_conversation_number_out_of_range(self):
        """Test conversation number that's out of range."""
        list_data = self._load_and_fix_conversations_fixture("conversations_list_success.json")

        responses.add(
            responses.GET,
            "https://api.test.com/conversations",
            json=list_data,
            status=200
        )

        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

            result = self.runner.invoke(conv, ["show", "99"])

            assert result.exit_code == 0
            assert "Conversation number 99 is out of range (1-2)" in result.output

    def test_api_error_handling(self):
        """Test error handling when API calls fail."""
        with patch("ohc.command_utils.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_server_config.return_value = self.mock_config

            with patch("ohc.command_utils.OpenHandsAPI") as mock_api_class:
                mock_api = Mock()
                mock_api.search_conversations.side_effect = Exception("API Error")
                mock_api_class.return_value = mock_api

                result = self.runner.invoke(conv, ["list"])

                assert result.exit_code == 0
                assert "Failed to list conversations: API Error" in result.output
