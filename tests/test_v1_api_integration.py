"""
Integration tests for OpenHands v1 API using fixtures.

These tests use recorded API responses to test the v1 API client
without making actual HTTP requests.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest
import responses

from ohc.v1.api import OpenHandsAPI


class TestOpenHandsV1APIIntegration:
    """Integration tests for OpenHands v1 API using fixtures."""

    @pytest.fixture
    def v1_fixtures_dir(self) -> Path:
        """Return the path to the v1 sanitized fixtures directory."""
        return Path(__file__).parent / "fixtures" / "v1" / "sanitized"

    @pytest.fixture
    def load_v1_fixture(self, v1_fixtures_dir):
        """Factory fixture to load a specific v1 fixture file."""

        def _load_fixture(fixture_name: str) -> Dict[str, Any]:
            fixture_file = v1_fixtures_dir / f"{fixture_name}.json"
            if not fixture_file.exists():
                raise FileNotFoundError(f"V1 fixture file not found: {fixture_file}")

            with open(fixture_file, "r") as f:
                return json.load(f)

        return _load_fixture

    @pytest.fixture
    def api_client(self) -> OpenHandsAPI:
        """Create an OpenHands v1 API client for testing."""
        return OpenHandsAPI("test_api_key", "https://app.all-hands.dev/api/")

    @responses.activate
    def test_test_connection_success(self, api_client, load_v1_fixture):
        """Test successful connection test using v1 events/count endpoint."""
        fixture = load_v1_fixture("events_count_basic")
        
        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        result = api_client.test_connection()
        assert result is True

    @responses.activate
    def test_test_connection_failure(self, api_client):
        """Test connection failure."""
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/v1/events/count",
            json={"error": "Unauthorized"},
            status=401,
        )

        result = api_client.test_connection()
        assert result is False

    @responses.activate
    def test_search_events(self, api_client, load_v1_fixture):
        """Test searching events."""
        fixture = load_v1_fixture("events_search_basic")
        
        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        events = api_client.search_events(limit=10, offset=0)
        
        assert isinstance(events, list)
        assert len(events) == 2
        assert events[0]["type"] == "action"
        assert events[1]["type"] == "observation"

    @responses.activate
    def test_search_events_unauthorized(self, api_client, load_v1_fixture):
        """Test searching events with unauthorized access."""
        fixture = load_v1_fixture("events_search_unauthorized")
        
        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        with pytest.raises(Exception) as exc_info:
            api_client.search_events()
        
        assert "Unauthorized" in str(exc_info.value)

    @responses.activate
    def test_get_events_count(self, api_client, load_v1_fixture):
        """Test getting events count."""
        fixture = load_v1_fixture("events_count_basic")
        
        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        count = api_client.get_events_count()
        assert count == 42

    @responses.activate
    def test_search_app_conversations(self, api_client, load_v1_fixture):
        """Test searching app conversations."""
        fixture = load_v1_fixture("app_conversations_search_basic")
        
        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        conversations = api_client.search_app_conversations(limit=10, offset=0)
        
        assert isinstance(conversations, list)
        assert len(conversations) == 2
        assert conversations[0]["title"] == "Test Conversation 1"
        assert conversations[0]["status"] == "completed"
        assert conversations[1]["status"] == "running"

    @responses.activate
    def test_search_conversations_compatibility(self, api_client, load_v1_fixture):
        """Test the compatibility method for searching conversations."""
        fixture = load_v1_fixture("app_conversations_search_basic")
        
        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        # This should delegate to search_app_conversations
        conversations = api_client.search_conversations(limit=10, offset=0)
        
        assert isinstance(conversations, list)
        assert len(conversations) == 2

    def test_unimplemented_methods(self, api_client):
        """Test that unimplemented compatibility methods raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            api_client.get_conversation("test_id")
        
        with pytest.raises(NotImplementedError):
            api_client.start_conversation({})
        
        with pytest.raises(NotImplementedError):
            api_client.get_conversation_changes("test_id")
        
        with pytest.raises(NotImplementedError):
            api_client.get_file_content("test_id", "test_path")
        
        with pytest.raises(NotImplementedError):
            api_client.download_workspace_archive("test_id")
        
        with pytest.raises(NotImplementedError):
            api_client.get_trajectory("test_id")