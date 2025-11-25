"""
Integration tests for the OpenHands API client using fixtures.

These tests use recorded and sanitized API responses to test the API client
without making actual HTTP requests.
"""

import pytest
import responses

from ohc.api import OpenHandsAPI


class TestOpenHandsAPIIntegration:
    """Integration tests for OpenHandsAPI using fixtures."""

    @pytest.fixture
    def api_client(self) -> OpenHandsAPI:
        """Create an API client instance for testing."""
        return OpenHandsAPI(
            api_key="fake-api-key", base_url="https://app.all-hands.dev/api/"
        )

    @responses.activate
    def test_test_connection_success(self, api_client, fixture_loader):
        """Test successful connection test using fixture."""
        # Load fixture and set up mock
        fixture = fixture_loader.load("options_models")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/options/models",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        # Test the connection
        result = api_client.test_connection()
        assert result is True

    @responses.activate
    def test_test_connection_failure(self, api_client):
        """Test connection failure."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/options/models", status=401
        )

        result = api_client.test_connection()
        assert result is False

    @responses.activate
    def test_search_conversations(self, api_client, fixture_loader):
        """Test searching conversations using fixture."""
        fixture = fixture_loader.load("conversations_list_success")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        result = api_client.search_conversations(limit=5)

        assert isinstance(result, dict)
        assert "conversations" in result
        assert isinstance(result["conversations"], list)
        assert len(result["conversations"]) == 2
        assert result["conversations"][0]["title"] == "Example Conversation 1"

    @responses.activate
    def test_search_conversations_with_pagination(self, api_client, fixture_loader):
        """Test searching conversations with pagination using fixture."""
        fixture = fixture_loader.load("conversations_list_paginated_success")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        result = api_client.search_conversations(page_id="some-page-id", limit=2)

        assert isinstance(result, dict)
        assert "conversations" in result
        assert result["has_more"] is True
        assert result["page_id"] == "next-page-id"

    @responses.activate
    def test_search_conversations_unauthorized(self, api_client):
        """Test unauthorized access to conversations."""
        responses.add(
            responses.GET, "https://app.all-hands.dev/api/conversations", status=401
        )

        with pytest.raises(Exception) as exc_info:
            api_client.search_conversations()

        assert "API key does not have permission" in str(exc_info.value)

    @responses.activate
    def test_get_conversation(self, api_client, fixture_loader):
        """Test getting conversation details using fixture."""
        fixture = fixture_loader.load("conversation_details")
        conversation_id = "fake-conversation-id"

        responses.add(
            responses.GET,
            f"https://app.all-hands.dev/api/conversations/{conversation_id}",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        result = api_client.get_conversation(conversation_id)

        assert isinstance(result, dict)
        assert "conversation_id" in result

    @responses.activate
    def test_start_conversation(self, api_client):
        """Test starting a conversation."""
        conversation_id = "fake-conversation-id"

        responses.add(
            responses.POST,
            f"https://app.all-hands.dev/api/conversations/{conversation_id}/start",
            json={"status": "started", "runtime_id": "work-1-fakeworkspace001"},
            status=200,
        )

        result = api_client.start_conversation(conversation_id, ["github"])

        assert isinstance(result, dict)
        assert result["status"] == "started"

    @responses.activate
    def test_start_conversation_failure(self, api_client):
        """Test conversation start failure."""
        conversation_id = "fake-conversation-id"

        responses.add(
            responses.POST,
            f"https://app.all-hands.dev/api/conversations/{conversation_id}/start",
            status=500,
            body="Internal Server Error",
        )

        with pytest.raises(Exception) as exc_info:
            api_client.start_conversation(conversation_id)

        assert "API call failed" in str(exc_info.value)

    @responses.activate
    def test_get_conversation_changes_with_runtime(self, api_client, fixture_loader):
        """Test getting conversation changes using runtime URL and fixture."""
        try:
            fixture = fixture_loader.load("git_changes")
        except FileNotFoundError:
            # Skip test if fixture doesn't exist
            pytest.skip("git_changes fixture not available")

        conversation_id = "fake-conversation-id"
        runtime_url = "https://work-1-fakeworkspace001.prod-runtime.all-hands.dev"
        session_api_key = "sess_fakexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

        responses.add(
            responses.GET,
            f"{runtime_url}/api/conversations/{conversation_id}/git/changes",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        result = api_client.get_conversation_changes(
            conversation_id, runtime_url, session_api_key
        )

        assert isinstance(result, list)

    @responses.activate
    def test_get_conversation_changes_not_found(self, api_client):
        """Test getting conversation changes when not found."""
        conversation_id = "fake-conversation-id"
        runtime_url = "https://work-1-fakeworkspace001.prod-runtime.all-hands.dev"

        responses.add(
            responses.GET,
            f"{runtime_url}/api/conversations/{conversation_id}/git/changes",
            status=404,
        )

        result = api_client.get_conversation_changes(conversation_id, runtime_url)
        assert result == []

    @responses.activate
    def test_get_file_content(self, api_client):
        """Test getting file content."""
        conversation_id = "fake-conversation-id"
        runtime_url = "https://work-1-fakeworkspace001.prod-runtime.all-hands.dev"
        file_path = "example.py"

        responses.add(
            responses.GET,
            f"{runtime_url}/api/conversations/{conversation_id}/select-file",
            json={"code": "print('Hello, World!')"},
            status=200,
        )

        result = api_client.get_file_content(
            conversation_id, file_path, runtime_url, "fake-session-key"
        )

        assert result == "print('Hello, World!')"

    @responses.activate
    def test_get_file_content_not_found(self, api_client):
        """Test getting file content when file not found."""
        conversation_id = "fake-conversation-id"
        runtime_url = "https://work-1-fakeworkspace001.prod-runtime.all-hands.dev"
        file_path = "nonexistent.txt"

        responses.add(
            responses.GET,
            f"{runtime_url}/api/conversations/{conversation_id}/select-file",
            status=404,
        )

        with pytest.raises(Exception) as exc_info:
            api_client.get_file_content(conversation_id, file_path, runtime_url)

        assert "File not found" in str(exc_info.value)

    @responses.activate
    def test_download_workspace_archive(self, api_client):
        """Test downloading workspace archive."""
        conversation_id = "fake-conversation-id"
        runtime_url = "https://work-1-fakeworkspace001.prod-runtime.all-hands.dev"
        fake_zip_content = b"PK\x03\x04fake zip content"

        responses.add(
            responses.GET,
            f"{runtime_url}/api/conversations/{conversation_id}/zip-directory",
            body=fake_zip_content,
            status=200,
            headers={"Content-Type": "application/zip"},
        )

        result = api_client.download_workspace_archive(
            conversation_id, runtime_url, "fake-session-key"
        )

        assert result == fake_zip_content

    @responses.activate
    def test_get_trajectory(self, api_client, fixture_loader):
        """Test getting trajectory data using fixture."""
        try:
            fixture = fixture_loader.load("trajectory")
        except FileNotFoundError:
            # Skip test if fixture doesn't exist
            pytest.skip("trajectory fixture not available")

        conversation_id = "fake-conversation-id"
        runtime_url = "https://work-1-fakeworkspace001.prod-runtime.all-hands.dev"
        session_api_key = "sess_fakexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

        responses.add(
            responses.GET,
            f"{runtime_url}/api/conversations/{conversation_id}/trajectory",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        result = api_client.get_trajectory(
            conversation_id, runtime_url, session_api_key
        )

        assert isinstance(result, dict)


# VCR.py integration is available but we're using pre-recorded fixtures
# for more reliable and faster testing. If needed, VCR can be used to
# record new interactions by using the @pytest.mark.vcr() decorator.
