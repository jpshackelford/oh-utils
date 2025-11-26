"""
Unit tests for the OpenHands API client.

These tests focus on testing the API client logic, error handling,
and edge cases using mocked responses.
"""

from unittest.mock import patch

import pytest
import requests
import responses

from ohc.api import OpenHandsAPI


class TestOpenHandsAPI:
    """Unit tests for OpenHandsAPI class."""

    def test_init_default_base_url(self):
        """Test API client initialization with default base URL."""
        api = OpenHandsAPI("test-key")
        assert api.api_key == "test-key"
        assert api.base_url == "https://app.all-hands.dev/api/"
        assert api.session.headers["X-Session-API-Key"] == "test-key"
        assert api.session.headers["Content-Type"] == "application/json"

    def test_init_custom_base_url(self):
        """Test API client initialization with custom base URL."""
        custom_url = "https://custom.example.com/api"
        api = OpenHandsAPI("test-key", custom_url)
        assert api.api_key == "test-key"
        assert api.base_url == "https://custom.example.com/api/"

    def test_init_base_url_trailing_slash_handling(self):
        """Test that base URL trailing slash is handled correctly."""
        # URL without trailing slash
        api1 = OpenHandsAPI("test-key", "https://example.com/api")
        assert api1.base_url == "https://example.com/api/"

        # URL with trailing slash
        api2 = OpenHandsAPI("test-key", "https://example.com/api/")
        assert api2.base_url == "https://example.com/api/"

    @responses.activate
    def test_test_connection_success(self):
        """Test successful connection test."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/options/models", status=200
        )

        api = OpenHandsAPI("test-key")
        assert api.test_connection() is True

    @responses.activate
    def test_test_connection_failure_http_error(self):
        """Test connection failure due to HTTP error."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/options/models", status=401
        )

        api = OpenHandsAPI("test-key")
        assert api.test_connection() is False

    def test_test_connection_failure_exception(self):
        """Test connection failure due to network exception."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get", side_effect=requests.ConnectionError()):
            assert api.test_connection() is False

    @responses.activate
    def test_search_conversations_success(self):
        """Test successful conversation search."""
        mock_response = {
            "conversations": [{"conversation_id": "123", "title": "Test Conversation"}],
            "total": 1,
        }

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.search_conversations(limit=10)

        assert result == mock_response
        assert len(responses.calls) == 1
        assert responses.calls[0].request.params["limit"] == "10"

    @responses.activate
    def test_search_conversations_with_pagination(self):
        """Test conversation search with pagination."""
        mock_response = {"conversations": [], "total": 0}

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.search_conversations(page_id="page123", limit=5)

        assert result == mock_response
        assert len(responses.calls) == 1
        request_params = responses.calls[0].request.params
        assert request_params["limit"] == "5"
        assert request_params["page_id"] == "page123"

    @responses.activate
    def test_search_conversations_unauthorized(self):
        """Test conversation search with unauthorized error."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/conversations", status=401
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.search_conversations()

        assert "API key does not have permission" in str(exc_info.value)
        assert "full API key" in str(exc_info.value)

    @responses.activate
    def test_search_conversations_other_http_error(self):
        """Test conversation search with other HTTP errors."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/conversations", status=500
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(requests.exceptions.HTTPError):
            api.search_conversations()

    @responses.activate
    def test_get_conversation_success(self):
        """Test successful conversation retrieval."""
        mock_response = {
            "conversation_id": "123",
            "title": "Test Conversation",
            "status": "RUNNING",
        }

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation("123")

        assert result == mock_response

    @responses.activate
    def test_get_conversation_not_found_none_response(self):
        """Test conversation retrieval when API returns None."""
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123",
            body="null",
            status=200,
            content_type="application/json",
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_conversation("123")

        assert "Conversation '123' not found" in str(exc_info.value)

    @responses.activate
    def test_get_conversation_http_error(self):
        """Test conversation retrieval with HTTP error."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/conversations/123", status=404
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(requests.exceptions.HTTPError):
            api.get_conversation("123")

    @responses.activate
    def test_start_conversation_success(self):
        """Test successful conversation start."""
        mock_response = {"status": "started", "url": "https://example.com"}

        responses.add(
            responses.POST,
            "https://app.all-hands.dev/api/conversations/123/start",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.start_conversation("123")

        assert result == mock_response

        # Check request body
        request_body = responses.calls[0].request.body
        import json

        assert json.loads(request_body) == {"providers_set": ["github"]}

    @responses.activate
    def test_start_conversation_with_custom_providers(self):
        """Test conversation start with custom providers."""
        mock_response = {"status": "started"}

        responses.add(
            responses.POST,
            "https://app.all-hands.dev/api/conversations/123/start",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.start_conversation("123", providers_set=["custom", "provider"])

        assert result == mock_response

        # Check request body
        request_body = responses.calls[0].request.body
        import json

        assert json.loads(request_body) == {"providers_set": ["custom", "provider"]}

    @responses.activate
    def test_start_conversation_failure(self):
        """Test conversation start failure."""
        responses.add(
            responses.POST,
            "https://app.all-hands.dev/api/conversations/123/start",
            body="Server Error",
            status=500,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.start_conversation("123")

        assert "API call failed" in str(exc_info.value)
        assert "HTTP 500" in str(exc_info.value)

    @responses.activate
    def test_get_conversation_changes_with_runtime_url(self):
        """Test getting conversation changes with runtime URL."""
        mock_response = [
            {"file": "test.py", "status": "modified"},
            {"file": "new.py", "status": "added"},
        ]

        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation_changes(
            "123",
            runtime_url="https://runtime.example.com",
            session_api_key="session-key",
        )

        assert result == mock_response

        # Check headers
        request_headers = responses.calls[0].request.headers
        assert request_headers["X-Session-API-Key"] == "session-key"

    @responses.activate
    def test_get_conversation_changes_with_runtime_url_no_session_key(self):
        """Test getting conversation changes with runtime URL but no session key."""
        mock_response = []

        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation_changes(
            "123", runtime_url="https://runtime.example.com"
        )

        assert result == mock_response

        # Check headers - should use Bearer token
        request_headers = responses.calls[0].request.headers
        assert request_headers["Authorization"] == "Bearer test-key"

    @responses.activate
    def test_get_conversation_changes_without_runtime_url(self):
        """Test getting conversation changes without runtime URL."""
        mock_response = []

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123/git/changes",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation_changes("123")

        assert result == mock_response

    @responses.activate
    def test_get_conversation_changes_not_found(self):
        """Test getting conversation changes when not found."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            status=404,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation_changes(
            "123", runtime_url="https://runtime.example.com"
        )

        assert result == []

    @responses.activate
    def test_get_conversation_changes_server_error(self):
        """Test getting conversation changes with server error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            status=500,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_conversation_changes(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Git repository not available or corrupted" in str(exc_info.value)

    @responses.activate
    def test_get_conversation_changes_http_error_404(self):
        """Test getting conversation changes with HTTP 404 error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            status=404,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation_changes(
            "123", runtime_url="https://runtime.example.com"
        )

        # Should return empty list for 404
        assert result == []

    @responses.activate
    def test_get_conversation_changes_http_error_500(self):
        """Test getting conversation changes with HTTP 500 error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            status=500,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_conversation_changes(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Git repository not available or corrupted" in str(exc_info.value)

    @responses.activate
    def test_get_conversation_changes_other_http_error(self):
        """Test getting conversation changes with other HTTP error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/git/changes",
            status=403,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_conversation_changes(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Failed to get changes: HTTP 403" in str(exc_info.value)

    def test_get_conversation_changes_network_error(self):
        """Test getting conversation changes with network error."""
        api = OpenHandsAPI("test-key")

        with patch.object(
            api.session, "get", side_effect=requests.ConnectionError("Network error")
        ):
            with pytest.raises(Exception) as exc_info:
                api.get_conversation_changes(
                    "123", runtime_url="https://runtime.example.com"
                )

            assert "API call failed" in str(exc_info.value)

    @responses.activate
    def test_get_file_content_success(self):
        """Test successful file content retrieval."""
        mock_response = {"code": "print('Hello, World!')"}

        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/select-file",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_file_content(
            "123",
            "test.py",
            runtime_url="https://runtime.example.com",
            session_api_key="session-key",
        )

        assert result == "print('Hello, World!')"

        # Check query parameters
        request_params = responses.calls[0].request.params
        assert request_params["file"] == "test.py"

    @responses.activate
    def test_get_file_content_fallback_response_format(self):
        """Test file content retrieval with fallback response format."""
        mock_response = "Direct content string"

        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/select-file",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_file_content(
            "123", "test.py", runtime_url="https://runtime.example.com"
        )

        assert result == "Direct content string"

    @responses.activate
    def test_get_file_content_not_found(self):
        """Test file content retrieval when file not found."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/select-file",
            status=404,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_file_content(
                "123", "test.py", runtime_url="https://runtime.example.com"
            )

        assert "File not found: test.py" in str(exc_info.value)

    @responses.activate
    def test_get_file_content_unauthorized(self):
        """Test file content retrieval with unauthorized error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/select-file",
            status=401,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_file_content(
                "123", "test.py", runtime_url="https://runtime.example.com"
            )

        assert "Authentication failed - invalid session API key" in str(exc_info.value)

    @responses.activate
    def test_get_file_content_server_error(self):
        """Test file content retrieval with server error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/select-file",
            status=500,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_file_content(
                "123", "test.py", runtime_url="https://runtime.example.com"
            )

        assert "Server error - file may be inaccessible" in str(exc_info.value)

    @responses.activate
    def test_get_file_content_other_http_error(self):
        """Test file content retrieval with other HTTP error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/select-file",
            status=403,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_file_content(
                "123", "test.py", runtime_url="https://runtime.example.com"
            )

        assert "Failed to get file content: HTTP 403" in str(exc_info.value)

    def test_get_file_content_network_error(self):
        """Test file content retrieval with network error."""
        api = OpenHandsAPI("test-key")

        with patch.object(
            api.session, "get", side_effect=requests.ConnectionError("Network error")
        ):
            with pytest.raises(Exception) as exc_info:
                api.get_file_content(
                    "123", "test.py", runtime_url="https://runtime.example.com"
                )

            assert "API call failed" in str(exc_info.value)

    @responses.activate
    def test_download_workspace_archive_success(self):
        """Test successful workspace archive download."""
        mock_content = b"ZIP file content"

        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/zip-directory",
            body=mock_content,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.download_workspace_archive(
            "123",
            runtime_url="https://runtime.example.com",
            session_api_key="session-key",
        )

        assert result == mock_content

    @responses.activate
    def test_download_workspace_archive_not_found(self):
        """Test workspace archive download when not found."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/zip-directory",
            status=404,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.download_workspace_archive(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Workspace not found for conversation 123" in str(exc_info.value)

    @responses.activate
    def test_download_workspace_archive_unauthorized(self):
        """Test workspace archive download with unauthorized error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/zip-directory",
            status=401,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.download_workspace_archive(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Authentication failed - invalid session API key" in str(exc_info.value)

    @responses.activate
    def test_download_workspace_archive_server_error(self):
        """Test workspace archive download with server error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/zip-directory",
            status=500,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.download_workspace_archive(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Server error - workspace may be inaccessible" in str(exc_info.value)

    @responses.activate
    def test_download_workspace_archive_other_http_error(self):
        """Test workspace archive download with other HTTP error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/zip-directory",
            status=403,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.download_workspace_archive(
                "123", runtime_url="https://runtime.example.com"
            )

        assert "Failed to download workspace: HTTP 403" in str(exc_info.value)

    def test_download_workspace_archive_network_error(self):
        """Test workspace archive download with network error."""
        api = OpenHandsAPI("test-key")

        with patch.object(
            api.session, "get", side_effect=requests.ConnectionError("Network error")
        ):
            with pytest.raises(Exception) as exc_info:
                api.download_workspace_archive(
                    "123", runtime_url="https://runtime.example.com"
                )

            assert "API call failed" in str(exc_info.value)

    @responses.activate
    def test_get_trajectory_success(self):
        """Test successful trajectory retrieval."""
        mock_response = {"trajectory": [{"step": 1, "action": "test"}]}

        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/trajectory",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_trajectory("123", "https://runtime.example.com", "session-key")

        assert result == mock_response

    @responses.activate
    def test_get_trajectory_not_found(self):
        """Test trajectory retrieval when not found."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/trajectory",
            status=404,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_trajectory("123", "https://runtime.example.com", "session-key")

        assert "Trajectory not found for conversation 123" in str(exc_info.value)

    @responses.activate
    def test_get_trajectory_unauthorized(self):
        """Test trajectory retrieval with unauthorized error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/trajectory",
            status=401,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_trajectory("123", "https://runtime.example.com", "session-key")

        assert "Authentication failed - invalid session API key" in str(exc_info.value)

    @responses.activate
    def test_get_trajectory_server_error(self):
        """Test trajectory retrieval with server error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/trajectory",
            status=500,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_trajectory("123", "https://runtime.example.com", "session-key")

        assert "Server error - trajectory may be inaccessible" in str(exc_info.value)

    @responses.activate
    def test_get_trajectory_other_http_error(self):
        """Test trajectory retrieval with other HTTP error."""
        responses.add(
            responses.GET,
            "https://runtime.example.com/api/conversations/123/trajectory",
            status=403,
        )

        api = OpenHandsAPI("test-key")

        with pytest.raises(Exception) as exc_info:
            api.get_trajectory("123", "https://runtime.example.com", "session-key")

        assert "Failed to get trajectory: HTTP 403" in str(exc_info.value)

    def test_get_trajectory_network_error(self):
        """Test trajectory retrieval with network error."""
        api = OpenHandsAPI("test-key")

        with patch.object(
            api.session, "get", side_effect=requests.ConnectionError("Network error")
        ):
            with pytest.raises(Exception) as exc_info:
                api.get_trajectory("123", "https://runtime.example.com", "session-key")

            assert "API call failed" in str(exc_info.value)

    @responses.activate
    def test_get_conversation_changes_without_runtime_url_fallback(self):
        """Test getting conversation changes without runtime URL (fallback path)."""
        mock_response = []

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123/git/changes",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_conversation_changes("123", runtime_url=None)

        assert result == mock_response

    @responses.activate
    def test_get_file_content_without_runtime_url_fallback(self):
        """Test getting file content without runtime URL (fallback path)."""
        mock_response = {"code": "test content"}

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123/select-file",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_file_content("123", "test.py", runtime_url=None)

        assert result == "test content"

    @responses.activate
    def test_download_workspace_archive_without_runtime_url_fallback(self):
        """Test downloading workspace archive without runtime URL (fallback path)."""
        mock_content = b"ZIP content"

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123/zip-directory",
            body=mock_content,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.download_workspace_archive("123", runtime_url=None)

        assert result == mock_content

    @responses.activate
    def test_get_trajectory_without_runtime_url_fallback(self):
        """Test getting trajectory without runtime URL (fallback path)."""
        mock_response = {"trajectory": []}

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations/123/trajectory",
            json=mock_response,
            status=200,
        )

        api = OpenHandsAPI("test-key")
        result = api.get_trajectory("123", runtime_url=None, session_api_key="key")

        assert result == mock_response
