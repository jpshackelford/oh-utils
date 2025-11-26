"""
Unit tests for command utilities.

Tests the shared decorators and utilities used across CLI commands.
"""

from unittest.mock import Mock, patch

from ohc.api import OpenHandsAPI
from ohc.command_utils import (
    handle_missing_server_config,
    resolve_conversation_id,
    with_server_config,
)


class TestWithServerConfigDecorator:
    """Test the @with_server_config decorator."""

    def test_decorator_with_valid_server_config(self):
        """Test decorator passes API instance when server config exists."""
        mock_config_manager = Mock()
        mock_config_manager.get_server_config.return_value = {
            "api_key": "test-key",
            "url": "https://test.example.com/api/"
        }

        @with_server_config
        def test_command(api: OpenHandsAPI, server: str = None) -> str:
            return f"API base URL: {api.base_url}"

        with patch('ohc.command_utils.ConfigManager', return_value=mock_config_manager):
            result = test_command(server="test-server")

        assert result == "API base URL: https://test.example.com/api/"
        mock_config_manager.get_server_config.assert_called_once_with("test-server")

    def test_decorator_with_missing_server_config(self, capsys):
        """Test decorator handles missing server config gracefully."""
        mock_config_manager = Mock()
        mock_config_manager.get_server_config.return_value = None

        @with_server_config
        def test_command(api: OpenHandsAPI, server: str = None) -> str:
            return "Should not reach here"

        with patch('ohc.command_utils.ConfigManager', return_value=mock_config_manager):
            result = test_command(server="missing-server")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Server 'missing-server' not found." in captured.err

    def test_decorator_with_no_default_server(self, capsys):
        """Test decorator handles missing default server config."""
        mock_config_manager = Mock()
        mock_config_manager.get_server_config.return_value = None

        @with_server_config
        def test_command(api: OpenHandsAPI, server: str = None) -> str:
            return "Should not reach here"

        with patch('ohc.command_utils.ConfigManager', return_value=mock_config_manager):
            result = test_command()

        assert result is None
        captured = capsys.readouterr()
        assert (
            "✗ No servers configured. Use 'ohc server add' to add a server."
            in captured.err
        )


class TestResolveConversationId:
    """Test conversation ID resolution logic."""

    def test_resolve_by_number_valid(self):
        """Test resolving conversation by valid number."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [
                {"conversation_id": "abc123"},
                {"conversation_id": "def456"},
                {"conversation_id": "ghi789"}
            ]
        }

        result = resolve_conversation_id(mock_api, "2")

        assert result == "def456"
        mock_api.search_conversations.assert_called_once_with(limit=100)

    def test_resolve_by_number_out_of_range(self, capsys):
        """Test resolving conversation by number out of range."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [{"conversation_id": "abc123"}]
        }

        result = resolve_conversation_id(mock_api, "5")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Conversation number 5 is out of range (1-1)" in captured.err

    def test_resolve_by_partial_id_single_match(self):
        """Test resolving by partial ID with single match."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [
                {"conversation_id": "abc123def", "title": "Test Conv 1"},
                {"conversation_id": "def456ghi", "title": "Test Conv 2"}
            ]
        }

        result = resolve_conversation_id(mock_api, "abc123")

        assert result == "abc123def"

    def test_resolve_by_partial_id_no_match(self, capsys):
        """Test resolving by partial ID with no matches."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [{"conversation_id": "abc123def"}]
        }

        result = resolve_conversation_id(mock_api, "xyz")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ No conversation found with ID starting with 'xyz'" in captured.err

    def test_resolve_by_partial_id_multiple_matches(self, capsys):
        """Test resolving by partial ID with multiple matches."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [
                {"conversation_id": "abc123def", "title": "Test Conv 1"},
                {"conversation_id": "abc456ghi", "title": "Test Conv 2"}
            ]
        }

        result = resolve_conversation_id(mock_api, "abc")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Multiple conversations match 'abc'" in captured.err
        assert "abc123def - Test Conv 1" in captured.out

    def test_resolve_by_full_id(self):
        """Test resolving by full conversation ID."""
        mock_api = Mock(spec=OpenHandsAPI)
        full_uuid = "12345678-1234-5678-9abc-123456789abc"  # 36 characters

        result = resolve_conversation_id(mock_api, full_uuid)

        assert result == full_uuid
        mock_api.search_conversations.assert_not_called()


class TestHandleMissingServerConfig:
    """Test missing server config error handling."""

    def test_handle_missing_named_server(self, capsys):
        """Test error message for missing named server."""
        handle_missing_server_config("production")

        captured = capsys.readouterr()
        assert "✗ Server 'production' not found." in captured.err

    def test_handle_missing_default_server(self, capsys):
        """Test error message for missing default server."""
        handle_missing_server_config(None)

        captured = capsys.readouterr()
        assert (
            "✗ No servers configured. Use 'ohc server add' to add a server."
            in captured.err
        )
