"""
Tests for API error handling and edge cases.

Tests the ohc.api module error handling including:
- Network failures
- HTTP error responses
- Authentication errors
- Invalid data handling
- Connection timeouts
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ohc.api import OpenHandsAPI


class TestOpenHandsAPIErrorHandling:
    """Test OpenHandsAPI error handling scenarios."""

    def test_init_basic(self):
        """Test basic API initialization."""
        api = OpenHandsAPI("test-key", "https://example.com/api/")

        assert api.api_key == "test-key"
        assert api.base_url == "https://example.com/api/"
        assert api.session.headers["X-Session-API-Key"] == "test-key"
        assert api.session.headers["Content-Type"] == "application/json"

    def test_init_base_url_normalization(self):
        """Test base URL normalization."""
        # Without trailing slash
        api1 = OpenHandsAPI("key", "https://example.com/api")
        assert api1.base_url == "https://example.com/api/"

        # With trailing slash
        api2 = OpenHandsAPI("key", "https://example.com/api/")
        assert api2.base_url == "https://example.com/api/"

        # Multiple trailing slashes
        api3 = OpenHandsAPI("key", "https://example.com/api///")
        assert api3.base_url == "https://example.com/api/"

    def test_test_connection_success(self):
        """Test successful connection test."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = api.test_connection()

            assert result is True
            mock_get.assert_called_once()

    def test_test_connection_http_error(self):
        """Test connection test with HTTP error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            result = api.test_connection()

            assert result is False

    def test_test_connection_network_error(self):
        """Test connection test with network error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            result = api.test_connection()

            assert result is False

    def test_test_connection_timeout(self):
        """Test connection test with timeout."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

            result = api.test_connection()

            assert result is False

    def test_search_conversations_success(self):
        """Test successful conversation search."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"conversations": [], "has_more": False}
            mock_get.return_value = mock_response

            result = api.search_conversations()

            assert result == {"conversations": [], "has_more": False}
            mock_get.assert_called_once()

    def test_search_conversations_with_pagination(self):
        """Test conversation search with pagination parameters."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"conversations": [], "has_more": True}
            mock_get.return_value = mock_response

            result = api.search_conversations(page_id="page123", limit=50)

            assert result == {"conversations": [], "has_more": True}
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert kwargs["params"]["page_id"] == "page123"
            assert kwargs["params"]["limit"] == 50

    def test_search_conversations_unauthorized(self):
        """Test conversation search with unauthorized error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.search_conversations()

            assert "API key does not have permission" in str(exc_info.value)

    def test_search_conversations_server_error(self):
        """Test conversation search with server error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(requests.exceptions.HTTPError):
                api.search_conversations()

    def test_search_conversations_network_error(self):
        """Test conversation search with network error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            with pytest.raises(requests.exceptions.ConnectionError):
                api.search_conversations()

    def test_get_conversation_success(self):
        """Test successful get conversation."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "conversation_id": "test-123",
                "title": "Test",
            }
            mock_get.return_value = mock_response

            result = api.get_conversation("test-123")

            assert result == {"conversation_id": "test-123", "title": "Test"}

    def test_get_conversation_not_found(self):
        """Test get conversation with not found error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(requests.exceptions.HTTPError):
                api.get_conversation("nonexistent")

    def test_start_conversation_success(self):
        """Test successful conversation start."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "conversation_id": "test-123",
                "status": "RUNNING",
            }
            mock_post.return_value = mock_response

            result = api.start_conversation("test-123")

            assert result == {"conversation_id": "test-123", "status": "RUNNING"}

    def test_start_conversation_with_providers(self):
        """Test conversation start with custom providers."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"conversation_id": "test-123"}
            mock_post.return_value = mock_response

            result = api.start_conversation(
                "test-123", providers_set=["github", "docker"]
            )

            assert result == {"conversation_id": "test-123"}
            args, kwargs = mock_post.call_args
            data = kwargs["json"]
            assert data["providers_set"] == ["github", "docker"]

    def test_start_conversation_error(self):
        """Test conversation start with error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_post.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.start_conversation("invalid-conv")

            assert "API call failed" in str(exc_info.value)

    def test_get_conversation_changes_success(self):
        """Test successful get conversation changes."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"path": "file.py", "status": "M"}]
            mock_get.return_value = mock_response

            result = api.get_conversation_changes(
                "conv-123", "https://runtime.com", "session-key"
            )

            assert result == [{"path": "file.py", "status": "M"}]

    def test_get_conversation_changes_no_runtime_url(self):
        """Test get conversation changes without runtime URL."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.get_conversation_changes("conv-123", None, "session-key")

            assert "Failed to get changes" in str(exc_info.value)

    def test_get_conversation_changes_no_session_key(self):
        """Test get conversation changes without session key."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            result = api.get_conversation_changes(
                "conv-123", "https://runtime.com", None
            )

            assert result == []

    def test_get_conversation_changes_git_error(self):
        """Test get conversation changes with git error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Git repository not available or corrupted"
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.get_conversation_changes(
                    "conv-123", "https://runtime.com", "session-key"
                )

            assert "Git repository not available or corrupted" in str(exc_info.value)

    def test_get_conversation_changes_other_http_error(self):
        """Test get conversation changes with other HTTP error (triggers HTTPError exception path)."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = (
                403  # Not 404 or 500, so will call raise_for_status
            )
            mock_response.text = "Forbidden"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.get_conversation_changes(
                    "conv-123", "https://runtime.com", "session-key"
                )

            assert "Failed to get changes: HTTP 403" in str(exc_info.value)

    def test_get_conversation_changes_404_returns_empty_list(self):
        """Test get conversation changes with 404 returns empty list."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not found"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            # 404 should return empty list, not raise exception
            result = api.get_conversation_changes(
                "conv-123", "https://runtime.com", "session-key"
            )

            assert result == []

    def test_get_file_content_success(self):
        """Test successful get file content."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": "print('hello')"}
            mock_response.raise_for_status = MagicMock()  # Don't raise
            mock_get.return_value = mock_response

            result = api.get_file_content(
                "conv-123", "file.py", "https://runtime.com", "session-key"
            )

            assert result == "print('hello')"

    def test_get_file_content_file_not_found(self):
        """Test get file content with file not found."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.get_file_content(
                    "conv-123", "nonexistent.py", "https://runtime.com", "session-key"
                )

            assert "File not found" in str(exc_info.value)

    def test_download_workspace_archive_success(self):
        """Test successful workspace archive download."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"archive content"
            mock_get.return_value = mock_response

            result = api.download_workspace_archive(
                "conv-123", "https://runtime.com", "session-key"
            )

            assert result == b"archive content"

    def test_download_workspace_archive_error(self):
        """Test workspace archive download with error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.download_workspace_archive(
                    "conv-123", "https://runtime.com", "session-key"
                )

            assert "Server error" in str(exc_info.value)

    def test_get_trajectory_success(self):
        """Test successful get trajectory."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"trajectory": [{"action": "init"}]}
            mock_get.return_value = mock_response

            result = api.get_trajectory(
                "conv-123", "https://runtime.com", "session-key"
            )

            assert result == {"trajectory": [{"action": "init"}]}

    def test_get_trajectory_fallback_url(self):
        """Test get trajectory with fallback to main URL."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"trajectory": []}
            mock_get.return_value = mock_response

            result = api.get_trajectory("conv-123", "", "")

            assert result == {"trajectory": []}

    def test_get_trajectory_runtime_url_no_session_key(self):
        """Test get trajectory with runtime URL but no session key (uses Bearer auth)."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"trajectory": [{"action": "test"}]}
            mock_get.return_value = mock_response

            # Runtime URL provided but no session key - should use Bearer auth
            result = api.get_trajectory("conv-123", "https://runtime.com", None)

            assert result == {"trajectory": [{"action": "test"}]}
            # Verify the call was made with Bearer authorization
            args, kwargs = mock_get.call_args
            assert "Authorization" in kwargs["headers"]
            assert kwargs["headers"]["Authorization"] == "Bearer test-key"

    def test_get_trajectory_not_found(self):
        """Test get trajectory with not found error."""
        api = OpenHandsAPI("test-key")

        with patch.object(api.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                api.get_trajectory("nonexistent", "https://runtime.com", "session-key")

            assert "Trajectory not found" in str(exc_info.value)
