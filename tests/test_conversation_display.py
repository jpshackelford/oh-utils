"""
Tests for conversation display functionality.

Tests the conversation_display module including:
- Conversation dataclass
- Display formatting methods
- Conversation details display
- Workspace changes display
"""

from unittest.mock import MagicMock, patch

from ohc.conversation_display import (
    Conversation,
    show_conversation_details,
    show_workspace_changes,
)


class TestConversation:
    """Test Conversation dataclass functionality."""

    def test_conversation_creation(self):
        """Test creating a Conversation instance."""
        conv = Conversation(
            id="test-conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key="session-key",
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://runtime-123.example.com/conv/test-conv-123",
        )

        assert conv.id == "test-conv-123"
        assert conv.title == "Test Conversation"
        assert conv.status == "RUNNING"
        assert conv.runtime_status == "READY"
        assert conv.runtime_id == "runtime-123"

    def test_from_api_response_with_url(self):
        """Test creating Conversation from API response with URL."""
        api_data = {
            "conversation_id": "api-conv-123",
            "title": "API Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-456.example.com/conv/api-conv-123",
            "session_api_key": "api-session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "api-conv-123"
        assert conv.title == "API Conversation"
        assert conv.status == "RUNNING"
        assert conv.runtime_status == "READY"
        assert conv.runtime_id == "runtime-456"  # Extracted from URL
        assert conv.url == "https://runtime-456.example.com/conv/api-conv-123"

    def test_from_api_response_without_url(self):
        """Test creating Conversation from API response without URL."""
        api_data = {
            "conversation_id": "no-url-conv",
            "title": "No URL Conversation",
            "status": "STOPPED",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "no-url-conv"
        assert conv.title == "No URL Conversation"
        assert conv.status == "STOPPED"
        assert conv.runtime_status is None
        assert conv.runtime_id is None
        assert conv.url is None

    def test_from_api_response_with_defaults(self):
        """Test creating Conversation with default values."""
        api_data = {
            "conversation_id": "minimal-conv",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "minimal-conv"
        assert conv.title == "Untitled"
        assert conv.status == "UNKNOWN"

    def test_from_api_response_invalid_url(self):
        """Test creating Conversation with invalid URL."""
        api_data = {
            "conversation_id": "invalid-url-conv",
            "title": "Invalid URL",
            "status": "RUNNING",
            "url": "not-a-valid-url",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "invalid-url-conv"
        assert conv.runtime_id is None  # Should handle invalid URL gracefully

    def test_is_active_running_with_runtime(self):
        """Test is_active returns True for running conversation with runtime."""
        conv = Conversation(
            id="active-conv",
            title="Active",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.is_active() is True

    def test_is_active_running_without_runtime(self):
        """Test is_active returns False for running conversation without runtime."""
        conv = Conversation(
            id="not-active-conv",
            title="Not Active",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.is_active() is False

    def test_is_active_stopped(self):
        """Test is_active returns False for stopped conversation."""
        conv = Conversation(
            id="stopped-conv",
            title="Stopped",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.is_active() is False

    def test_short_id(self):
        """Test short ID generation."""
        conv = Conversation(
            id="very-long-conversation-id-123456789",
            title="Test",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.short_id() == "very-lon"
        assert len(conv.short_id()) == 8

    def test_short_id_empty(self):
        """Test short ID with empty ID."""
        conv = Conversation(
            id="",
            title="Test",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.short_id() == "unknown"

    def test_formatted_title_short(self):
        """Test formatted title with short title."""
        conv = Conversation(
            id="test-conv",
            title="Short Title",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.formatted_title(50) == "Short Title"

    def test_formatted_title_long(self):
        """Test formatted title with long title."""
        conv = Conversation(
            id="test-conv",
            title="This is a very long conversation title that should be truncated",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        formatted = conv.formatted_title(20)
        assert len(formatted) == 20
        assert formatted.endswith("...")
        assert formatted == "This is a very lo..."

    def test_status_display_active(self):
        """Test status display for active conversation."""
        conv = Conversation(
            id="active-conv",
            title="Active",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.status_display() == "🟢 RUNNING"

    def test_status_display_stopped(self):
        """Test status display for stopped conversation."""
        conv = Conversation(
            id="stopped-conv",
            title="Stopped",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.status_display() == "🔴 STOPPED"

    def test_status_display_other(self):
        """Test status display for other status."""
        conv = Conversation(
            id="pending-conv",
            title="Pending",
            status="PENDING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.status_display() == "🟡 PENDING"


class TestShowConversationDetails:
    """Test show_conversation_details function."""

    def test_show_conversation_details_basic(self):
        """Test showing basic conversation details."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-conv-123",
            "title": "Test Conversation",
            "status": "STOPPED",
            "runtime_status": None,
            "url": None,
            "session_api_key": None,
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "test-conv-123")

        mock_api.get_conversation.assert_called_once_with("test-conv-123")

        # Verify print was called (basic smoke test)
        assert mock_print.called

    def test_show_conversation_details_with_url(self):
        """Test showing conversation details with URL."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "test-conv-123")

        # Verify print was called
        assert mock_print.called

    def test_show_conversation_details_active_with_changes(self):
        """Test showing active conversation details with changes."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "active-conv-123",
            "title": "Active Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/active-conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        mock_api.get_conversation_changes.return_value = [
            {"path": "file1.py", "status": "M"},
            {"path": "file2.py", "status": "A"},
            {"path": "file3.py", "status": "D"},
        ]

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "active-conv-123")

        mock_api.get_conversation_changes.assert_called_once_with(
            "active-conv-123", "https://runtime-123.example.com", "session-key"
        )

        # Verify print was called
        assert mock_print.called

    def test_show_conversation_details_active_no_changes(self):
        """Test showing active conversation details with no changes."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "active-conv-123",
            "title": "Active Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/active-conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        mock_api.get_conversation_changes.return_value = []

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "active-conv-123")

        # Verify print was called
        assert mock_print.called

    def test_show_conversation_details_changes_error(self):
        """Test showing conversation details when changes API fails."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "active-conv-123",
            "title": "Active Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/active-conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        mock_api.get_conversation_changes.side_effect = Exception("API error")

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "active-conv-123")

        # Verify print was called
        assert mock_print.called

    def test_show_conversation_details_api_error(self):
        """Test showing conversation details when main API fails."""
        mock_api = MagicMock()
        mock_api.get_conversation.side_effect = Exception("Conversation not found")

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "nonexistent-conv")

        # Verify print was called
        assert mock_print.called


class TestShowWorkspaceChanges:
    """Test show_workspace_changes function."""

    def test_show_workspace_changes_with_changes(self):
        """Test showing workspace changes when changes exist."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        mock_api.get_conversation_changes.return_value = [
            {"path": "src/main.py", "status": "M"},
            {"path": "tests/test_main.py", "status": "A"},
            {"path": "old_file.py", "status": "D"},
            {"path": "conflict.py", "status": "U"},
        ]

        with patch("builtins.print") as mock_print:
            show_workspace_changes(mock_api, "test-conv-123")

        mock_api.get_conversation_changes.assert_called_once_with(
            "test-conv-123", "https://runtime-123.example.com", "session-key"
        )

        # Verify print was called
        assert mock_print.called

    def test_show_workspace_changes_no_changes(self):
        """Test showing workspace changes when no changes exist."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        mock_api.get_conversation_changes.return_value = []

        with patch("builtins.print") as mock_print:
            show_workspace_changes(mock_api, "test-conv-123")

        # Verify print was called
        assert mock_print.called

    def test_show_workspace_changes_inactive_conversation(self):
        """Test showing workspace changes for inactive conversation."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-conv-123",
            "title": "Test Conversation",
            "status": "STOPPED",
            "runtime_status": None,
            "url": None,
            "session_api_key": None,
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        with patch("builtins.print") as mock_print:
            show_workspace_changes(mock_api, "test-conv-123")

        # Should not call get_conversation_changes for inactive conversation
        mock_api.get_conversation_changes.assert_not_called()
        # Verify print was called
        assert mock_print.called

    def test_show_workspace_changes_api_error(self):
        """Test showing workspace changes when API fails."""
        mock_api = MagicMock()
        mock_api.get_conversation.side_effect = Exception("API error")

        with patch("builtins.print") as mock_print:
            show_workspace_changes(mock_api, "test-conv-123")

        # Verify print was called
        assert mock_print.called

    def test_show_workspace_changes_git_error(self):
        """Test showing workspace changes with git repository error."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-123",
            "session_api_key": "session-key",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated_at": "2024-01-01T00:00:00Z",
        }
        mock_api.get_conversation_changes.side_effect = Exception(
            "Git repository not available or corrupted"
        )

        with patch("builtins.print") as mock_print:
            show_workspace_changes(mock_api, "test-conv-123")

        # Verify the git error message is displayed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(print_calls)

        assert "Git repository not available for conversation" in output

    def test_show_workspace_changes_auth_error(self):
        """Test showing workspace changes with authentication error."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-123",
            "session_api_key": "session-key",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated_at": "2024-01-01T00:00:00Z",
        }
        mock_api.get_conversation_changes.side_effect = Exception(
            "HTTP 401 Unauthorized"
        )

        with patch("builtins.print") as mock_print:
            show_workspace_changes(mock_api, "test-conv-123")

        # Verify the auth error message is displayed
        print_calls = []
        for call in mock_print.call_args_list:
            if call[0]:  # Check if there are positional arguments
                print_calls.append(str(call[0][0]))
        output = "\n".join(print_calls)

        assert "API key doesn't have permission to access git changes" in output

    def test_show_conversation_details_git_error(self):
        """Test showing conversation details with git repository error."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-123",
            "session_api_key": "session-key",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated_at": "2024-01-01T00:00:00Z",
        }
        mock_api.get_conversation_changes.side_effect = Exception(
            "Git repository not available or corrupted"
        )

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "test-123")

        # Verify the git error message is displayed
        print_calls = []
        for call in mock_print.call_args_list:
            if call[0]:  # Check if there are positional arguments
                print_calls.append(str(call[0][0]))
        output = "\n".join(print_calls)

        assert "Git repository not available for this conversation" in output

    def test_show_conversation_details_auth_error(self):
        """Test showing conversation details with authentication error."""
        mock_api = MagicMock()
        mock_api.get_conversation.return_value = {
            "conversation_id": "test-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/test-123",
            "session_api_key": "session-key",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated_at": "2024-01-01T00:00:00Z",
        }
        mock_api.get_conversation_changes.side_effect = Exception(
            "HTTP 401 Unauthorized"
        )

        with patch("builtins.print") as mock_print:
            show_conversation_details(mock_api, "test-123")

        # Verify the auth error message is displayed
        print_calls = []
        for call in mock_print.call_args_list:
            if call[0]:  # Check if there are positional arguments
                print_calls.append(str(call[0][0]))
        output = "\n".join(print_calls)

        assert "API key doesn't have permission to access git changes" in output
