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
            url="https://runtime.example.com/runtime123abc/api/conversations/test-conv-123",
        )

        assert conv.id == "test-conv-123"
        assert conv.title == "Test Conversation"
        assert conv.status == "RUNNING"
        assert conv.runtime_status == "READY"
        assert conv.runtime_id == "runtime-123"

    def test_from_api_response_with_url(self):
        """Test creating Conversation from API response with URL containing runtime_id in path."""
        api_data = {
            "conversation_id": "api-conv-123",
            "title": "API Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            # Path-based routing with runtime_id before /api/conversations
            "url": "https://runtime.example.com/runtime456abc/api/conversations/api-conv-123",
            "session_api_key": "api-session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "api-conv-123"
        assert conv.title == "API Conversation"
        assert conv.status == "RUNNING"
        assert conv.runtime_status == "READY"
        assert conv.runtime_id == "runtime456abc"  # Extracted from URL path
        assert (
            conv.url
            == "https://runtime.example.com/runtime456abc/api/conversations/api-conv-123"
        )

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

    def test_from_api_response_v1_format(self):
        """Test creating Conversation from v1 API response format."""
        api_data = {
            "id": "v1-conv-id",  # v1 uses 'id' instead of 'conversation_id'
            "title": "V1 Conversation",
            "sandbox_status": "RUNNING",  # v1 uses 'sandbox_status' instead of 'status'
            "execution_status": "idle",
            "conversation_url": "https://runtime.example.com/api/conversations/v1-conv-id",  # v1 uses 'conversation_url'
            "updated_at": "2024-01-15T10:30:00Z",  # v1 uses 'updated_at' instead of 'last_updated_at'
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "v1-conv-id"
        assert conv.title == "V1 Conversation"
        assert conv.status == "RUNNING"  # Should map sandbox_status to status
        assert conv.url == "https://runtime.example.com/api/conversations/v1-conv-id"
        assert conv.last_updated == "2024-01-15T10:30:00Z"

    def test_from_api_response_with_version(self):
        """Test creating Conversation with version information."""
        api_data = {
            "conversation_id": "versioned-conv",
            "title": "Versioned Conversation",
            "status": "RUNNING",
            "conversation_version": "V1",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "versioned-conv"
        assert conv.version == "V1"

    def test_from_api_response_with_direct_runtime_id(self):
        """Test creating Conversation with direct runtime_id field (enterprise servers)."""
        api_data = {
            "conversation_id": "enterprise-conv",
            "title": "Enterprise Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "runtime_id": "my-runtime-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "enterprise-conv"
        assert conv.runtime_id == "my-runtime-123"
        assert conv.is_active() is True

    def test_from_api_response_with_sandbox_id_fallback(self):
        """Test creating Conversation uses sandbox_id as fallback for runtime_id."""
        api_data = {
            "id": "v1-conv-id",
            "title": "V1 Conversation",
            "sandbox_status": "RUNNING",
            "sandbox_id": "SANDBOX_ID_001",
            "updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "v1-conv-id"
        assert conv.runtime_id == "SANDBOX_ID_001"  # Should fall back to sandbox_id

    def test_from_api_response_runtime_id_priority(self):
        """Test that direct runtime_id takes priority over URL extraction."""
        api_data = {
            "conversation_id": "priority-conv",
            "title": "Priority Test",
            "status": "RUNNING",
            "runtime_id": "direct-runtime",  # Should use this
            "url": "https://url-runtime.example.com/conv",  # Not this
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.runtime_id == "direct-runtime"  # Direct takes priority

    def test_from_api_response_relative_url_with_base(self):
        """Test that relative URLs are resolved using api_base_url (enterprise servers)."""
        api_data = {
            "conversation_id": "enterprise-conv-123",
            "title": "Enterprise Conversation",
            "status": "RUNNING",
            "runtime_status": "STATUS$READY",
            "url": "/api/conversations/enterprise-conv-123",  # Relative URL
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(
            api_data, api_base_url="https://myenterprise.example.com/api/"
        )

        # URL should be resolved to absolute
        assert (
            conv.url
            == "https://myenterprise.example.com/api/conversations/enterprise-conv-123"
        )
        # runtime_id should be None because the URL doesn't contain runtime info
        # (no path-based routing, and hostname 'myenterprise' is not a valid runtime_id pattern)
        assert conv.runtime_id is None

    def test_from_api_response_relative_url_without_base(self):
        """Test that relative URLs remain relative if no api_base_url provided."""
        api_data = {
            "conversation_id": "enterprise-conv-123",
            "title": "Enterprise Conversation",
            "status": "RUNNING",
            "url": "/api/conversations/enterprise-conv-123",  # Relative URL
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)  # No api_base_url

        # URL should remain relative
        assert conv.url == "/api/conversations/enterprise-conv-123"
        # runtime_id should be None since we can't parse a relative URL
        assert conv.runtime_id is None

    def test_from_api_response_path_based_runtime_url(self):
        """Test runtime_id extraction from path-based routing URL (enterprise)."""
        api_data = {
            "conversation_id": "enterprise-conv-123",
            "title": "Enterprise Conversation",
            "status": "RUNNING",
            "runtime_status": "STATUS$READY",
            # Path-based routing: https://runtime-server/{runtime_id}/api/conversations/{conv_id}
            "url": "https://runtime-server.example.com/abc123def456/api/conversations/enterprise-conv-123",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        # runtime_id should be extracted from path before /api/conversations
        assert conv.runtime_id == "abc123def456"

    def test_from_api_response_subdomain_runtime_url(self):
        """Test runtime_id extraction from subdomain-based URL (OpenHands Cloud)."""
        api_data = {
            "conversation_id": "cloud-conv-123",
            "title": "Cloud Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            # Subdomain-based routing: https://{runtime_id}.prod-runtime.all-hands.dev/...
            "url": "https://abcdef123456.prod-runtime.all-hands.dev/api/conversations/cloud-conv-123",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        # runtime_id should be extracted from subdomain (known runtime domain)
        assert conv.runtime_id == "abcdef123456"

    def test_from_api_response_non_runtime_subdomain(self):
        """Test that subdomains on non-runtime domains are NOT extracted as runtime_id."""
        api_data = {
            "conversation_id": "enterprise-conv-123",
            "title": "Enterprise Conversation",
            "status": "RUNNING",
            "runtime_status": "STATUS$READY",
            # URL with subdomain on a non-runtime domain - should NOT extract runtime_id
            "url": "https://myenterprise.example.com/api/conversations/enterprise-conv-123",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        # runtime_id should be None - 'myenterprise' is not on a known runtime domain
        assert conv.runtime_id is None

    def test_from_api_response_server_name_not_runtime_id(self):
        """Test that server names are not mistaken for runtime_id."""
        api_data = {
            "conversation_id": "enterprise-conv-123",
            "title": "Enterprise Conversation",
            "status": "RUNNING",
            "runtime_status": "STATUS$READY",
            # URL with server name (jps01) that should NOT be extracted as runtime_id
            "url": "https://jps01.r9.all-hands.dev/api/conversations/enterprise-conv-123",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        # runtime_id should be None - 'jps01' is a server name, not a runtime_id
        # (it's only 5 chars, runtime_ids are typically 10+ chars)
        assert conv.runtime_id is None

    def test_from_api_response_custom_runtime_domain_via_env(self):
        """Test runtime_id extraction with custom domain from OHC_RUNTIME_DOMAINS env var."""
        import os

        old_val = os.environ.get("OHC_RUNTIME_DOMAINS")
        try:
            os.environ["OHC_RUNTIME_DOMAINS"] = "runtime.company.com"
            api_data = {
                "conversation_id": "custom-conv-123",
                "title": "Custom Domain Conversation",
                "status": "RUNNING",
                "url": "https://myruntime001.runtime.company.com/api/conversations/custom-conv-123",
                "last_updated_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-15T10:00:00Z",
            }

            conv = Conversation.from_api_response(api_data)
            assert conv.runtime_id == "myruntime001"
        finally:
            if old_val is None:
                os.environ.pop("OHC_RUNTIME_DOMAINS", None)
            else:
                os.environ["OHC_RUNTIME_DOMAINS"] = old_val

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

    def test_get_runtime_base_url_with_url(self):
        """Test extracting runtime base URL from conversation URL."""
        conv = Conversation(
            id="test-conv",
            title="Test",
            status="RUNNING",
            runtime_status=None,
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://runtime.example.com/runtime123abc/api/conversations/test-conv",
        )

        assert conv.get_runtime_base_url() == "https://runtime.example.com"

    def test_get_runtime_base_url_without_url(self):
        """Test get_runtime_base_url returns None when no URL."""
        conv = Conversation(
            id="test-conv",
            title="Test",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        assert conv.get_runtime_base_url() is None

    def test_get_runtime_base_url_with_port(self):
        """Test get_runtime_base_url preserves port number."""
        conv = Conversation(
            id="test-conv",
            title="Test",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="http://localhost:8080/api/conversations/test-conv",
        )

        assert conv.get_runtime_base_url() == "http://localhost:8080"


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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-conv-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/active-conv-123",
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
            "active-conv-123", "https://runtime.example.com", "session-key"
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/active-conv-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/active-conv-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-conv-123",
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
            "test-conv-123", "https://runtime.example.com", "session-key"
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-conv-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-123",
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
            "url": "https://runtime.example.com/runtime123abc/api/conversations/test-123",
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
