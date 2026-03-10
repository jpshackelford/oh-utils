"""
Unit tests for command utilities.

Tests the shared decorators and utilities used across CLI commands,
including support for both v0 and v1 API response formats.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from ohc.command_utils import (
    _get_conversation_id,
    handle_missing_server_config,
    resolve_conversation_id,
    with_server_config,
)
from ohc.v0.api import OpenHandsAPI

# Path to fixture files
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(fixture_path: str) -> Dict[str, Any]:
    """Load a JSON fixture file."""
    full_path = FIXTURES_DIR / fixture_path
    with open(full_path) as f:
        return json.load(f)


# V0 API response fixture data (uses conversation_id)
V0_CONVERSATIONS_FIXTURE: List[Dict[str, Any]] = [
    {
        "conversation_id": "d2bfa2e22a0e4fef98882ab95258d4af",
        "title": "Test Release Process Before Merging to Main",
        "status": "RUNNING",
        "created_at": "2024-01-15T10:30:00.000Z",
    },
    {
        "conversation_id": "f342e61469234606aed568aa543808d4",
        "title": "Create Python Integration Tests with API Fixtures",
        "status": "RUNNING",
        "created_at": "2024-01-15T10:30:00.000Z",
    },
    {
        "conversation_id": "70d785223b8041898292dade15f10544",
        "title": "Fix release workflow dependency and permissions",
        "status": "STOPPED",
        "created_at": "2024-01-15T10:30:00.000Z",
    },
]

# V1 API response fixture data (uses id instead of conversation_id)
V1_CONVERSATIONS_FIXTURE: List[Dict[str, Any]] = [
    {
        "id": "CONV_ID_001_a1b2c3d4e5f6g7h8",
        "title": "Test Conversation 1",
        "status": "completed",
        "created_at": "2024-01-15T10:30:00.000Z",
        "updated_at": "2024-01-15T11:30:00.000Z",
        "user_id": "USER_ID_001",
        "metadata": {"model": "gpt-4"},
    },
    {
        "id": "CONV_ID_002_i9j0k1l2m3n4o5p6",
        "title": "Test Conversation 2",
        "status": "running",
        "created_at": "2024-01-15T12:30:00.000Z",
        "updated_at": "2024-01-15T13:30:00.000Z",
        "user_id": "USER_ID_001",
        "metadata": {"model": "claude-3-5-sonnet"},
    },
    {
        "id": "CONV_ID_003_q7r8s9t0u1v2w3x4",
        "title": "Test Conversation 3",
        "status": "paused",
        "created_at": "2024-01-15T14:30:00.000Z",
        "updated_at": "2024-01-15T15:30:00.000Z",
        "user_id": "USER_ID_001",
        "metadata": {"model": "gpt-4o"},
    },
]


class TestWithServerConfigDecorator:
    """Test the @with_server_config decorator."""

    def test_decorator_with_valid_server_config(self):
        """Test decorator passes API instance when server config exists."""
        mock_config_manager = Mock()
        mock_config_manager.get_server_config.return_value = {
            "api_key": "test-key",
            "url": "https://test.example.com/api/",
        }

        @with_server_config
        def test_command(api: OpenHandsAPI, server: str = None) -> str:
            return f"API base URL: {api.base_url}"

        with patch("ohc.command_utils.ConfigManager", return_value=mock_config_manager):
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

        with patch("ohc.command_utils.ConfigManager", return_value=mock_config_manager):
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

        with patch("ohc.command_utils.ConfigManager", return_value=mock_config_manager):
            result = test_command()

        assert result is None
        captured = capsys.readouterr()
        assert (
            "✗ No servers configured. Use 'ohc server add' to add a server."
            in captured.err
        )


class TestGetConversationId:
    """Test the _get_conversation_id helper function for v0/v1 compatibility."""

    def test_v0_response_format(self):
        """Test extracting ID from V0 API response (conversation_id field)."""
        v0_data = {"conversation_id": "abc123def", "title": "Test"}
        assert _get_conversation_id(v0_data) == "abc123def"

    def test_v1_response_format(self):
        """Test extracting ID from V1 API response (id field)."""
        v1_data = {"id": "xyz789uvw", "title": "Test V1"}
        assert _get_conversation_id(v1_data) == "xyz789uvw"

    def test_v0_takes_precedence_over_v1(self):
        """Test that conversation_id takes precedence if both exist."""
        mixed_data = {"conversation_id": "v0_id", "id": "v1_id", "title": "Test"}
        assert _get_conversation_id(mixed_data) == "v0_id"

    def test_empty_dict(self):
        """Test handling of empty dictionary."""
        assert _get_conversation_id({}) is None

    def test_neither_field_present(self):
        """Test handling when neither field is present."""
        data = {"title": "Test", "status": "running"}
        assert _get_conversation_id(data) is None

    def test_none_values(self):
        """Test handling when fields are None."""
        data = {"conversation_id": None, "id": None}
        assert _get_conversation_id(data) is None

    def test_empty_string_conversation_id_falls_back_to_id(self):
        """Test that empty conversation_id falls back to id."""
        data = {"conversation_id": "", "id": "valid_id"}
        # Empty string is falsy, so should fall back to id
        assert _get_conversation_id(data) == "valid_id"


class TestResolveConversationId:
    """Test conversation ID resolution logic."""

    # --- V0 API Tests (uses conversation_id field) ---

    def test_resolve_by_number_valid_v0(self):
        """Test resolving conversation by valid number with V0 API response."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V0_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "2")

        assert result == "f342e61469234606aed568aa543808d4"
        mock_api.search_conversations.assert_called_once_with(limit=100)

    def test_resolve_by_number_out_of_range_v0(self, capsys):
        """Test resolving conversation by number out of range."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [{"conversation_id": "abc123"}]
        }

        result = resolve_conversation_id(mock_api, "5")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Conversation number 5 is out of range (1-1)" in captured.err

    def test_resolve_by_partial_id_single_match_v0(self):
        """Test resolving by partial ID with single match using V0 format."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V0_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "d2bfa2e")

        assert result == "d2bfa2e22a0e4fef98882ab95258d4af"

    def test_resolve_by_partial_id_no_match_v0(self, capsys):
        """Test resolving by partial ID with no matches."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [{"conversation_id": "abc123def"}]
        }

        result = resolve_conversation_id(mock_api, "xyz")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ No conversation found with ID starting with 'xyz'" in captured.err

    def test_resolve_by_partial_id_multiple_matches_v0(self, capsys):
        """Test resolving by partial ID with multiple matches."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": [
                {"conversation_id": "abc123def", "title": "Test Conv 1"},
                {"conversation_id": "abc456ghi", "title": "Test Conv 2"},
            ]
        }

        result = resolve_conversation_id(mock_api, "abc")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Multiple conversations match 'abc'" in captured.err
        assert "abc123def - Test Conv 1" in captured.out

    def test_resolve_by_full_id_v0(self):
        """Test resolving by full conversation ID."""
        mock_api = Mock(spec=OpenHandsAPI)
        full_uuid = "12345678-1234-5678-9abc-123456789abc"  # 36 characters

        result = resolve_conversation_id(mock_api, full_uuid)

        assert result == full_uuid
        mock_api.search_conversations.assert_not_called()

    # --- V1 API Tests (uses id field instead of conversation_id) ---

    def test_resolve_by_number_valid_v1(self):
        """Test resolving conversation by valid number with V1 API response."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "1")

        assert result == "CONV_ID_001_a1b2c3d4e5f6g7h8"

    def test_resolve_by_number_v1_second_item(self):
        """Test resolving second conversation by number with V1 API response."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "2")

        assert result == "CONV_ID_002_i9j0k1l2m3n4o5p6"

    def test_resolve_by_number_v1_third_item(self):
        """Test resolving third conversation by number with V1 API response."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "3")

        assert result == "CONV_ID_003_q7r8s9t0u1v2w3x4"

    def test_resolve_by_partial_id_single_match_v1(self):
        """Test resolving by partial ID with single match using V1 format."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "CONV_ID_002")

        assert result == "CONV_ID_002_i9j0k1l2m3n4o5p6"

    def test_resolve_by_partial_id_multiple_matches_v1(self, capsys):
        """Test resolving by partial ID with multiple matches using V1 format."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        # "CONV_ID_" matches all three conversations
        result = resolve_conversation_id(mock_api, "CONV_ID_")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Multiple conversations match 'CONV_ID_'" in captured.err

    def test_resolve_by_partial_id_no_match_v1(self, capsys):
        """Test resolving by partial ID with no matches using V1 format."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "NONEXISTENT")

        assert result is None
        captured = capsys.readouterr()
        assert (
            "✗ No conversation found with ID starting with 'NONEXISTENT'"
            in captured.err
        )

    def test_resolve_by_number_out_of_range_v1(self, capsys):
        """Test resolving conversation by number out of range with V1 response."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V1_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "10")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Conversation number 10 is out of range (1-3)" in captured.err

    # --- Edge Cases ---

    def test_resolve_with_empty_results(self, capsys):
        """Test resolving when no conversations exist."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {"results": []}

        result = resolve_conversation_id(mock_api, "1")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Conversation number 1 is out of range (1-0)" in captured.err

    def test_resolve_mixed_v0_v1_responses(self):
        """Test resolving when API returns a mix of v0 and v1 formats."""
        mock_api = Mock(spec=OpenHandsAPI)
        mixed_results = [
            {"conversation_id": "v0_conv_abc123", "title": "V0 Style"},
            {"id": "v1_conv_xyz789", "title": "V1 Style"},
        ]
        mock_api.search_conversations.return_value = {"results": mixed_results}

        # First item (V0 format)
        result1 = resolve_conversation_id(mock_api, "1")
        assert result1 == "v0_conv_abc123"

        # Second item (V1 format)
        result2 = resolve_conversation_id(mock_api, "2")
        assert result2 == "v1_conv_xyz789"

    def test_resolve_partial_id_with_mixed_formats(self):
        """Test partial ID resolution with mixed v0/v1 formats."""
        mock_api = Mock(spec=OpenHandsAPI)
        mixed_results = [
            {"conversation_id": "abc123_v0_format", "title": "V0 Conv"},
            {"id": "abc456_v1_format", "title": "V1 Conv"},
        ]
        mock_api.search_conversations.return_value = {"results": mixed_results}

        # Single match from V0 format
        result = resolve_conversation_id(mock_api, "abc123")
        assert result == "abc123_v0_format"

    def test_resolve_zero_returns_none(self, capsys):
        """Test that requesting conversation 0 returns None."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V0_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "0")

        assert result is None
        captured = capsys.readouterr()
        assert "out of range" in captured.err

    def test_resolve_negative_number(self, capsys):
        """Test that negative numbers return None."""
        mock_api = Mock(spec=OpenHandsAPI)
        mock_api.search_conversations.return_value = {
            "results": V0_CONVERSATIONS_FIXTURE
        }

        result = resolve_conversation_id(mock_api, "-1")

        assert result is None
        captured = capsys.readouterr()
        assert "out of range" in captured.err


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
