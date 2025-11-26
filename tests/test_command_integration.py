"""
Integration tests for command utilities using fixtures.

Tests the shared command infrastructure with real API response fixtures
to ensure compatibility with the existing testing approach.
"""

from unittest.mock import Mock, patch

import responses

from ohc.api import OpenHandsAPI
from ohc.command_utils import resolve_conversation_id, with_server_config


class TestCommandIntegrationWithFixtures:
    """Test command utilities with fixture-based API responses."""

    @responses.activate
    def test_resolve_conversation_id_with_fixture_data(self, fixture_loader):
        """Test conversation ID resolution using fixture data."""
        # Load the conversations list fixture
        fixture = fixture_loader.load("conversations_list")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        api = OpenHandsAPI("fake-api-key", "https://app.all-hands.dev/api/")

        # Test resolving by number (should get first conversation)
        result = resolve_conversation_id(api, "1")
        assert result == "d2bfa2e22a0e4fef98882ab95258d4af"

    @responses.activate
    def test_resolve_conversation_id_by_partial_id_with_fixtures(self, fixture_loader):
        """Test partial ID resolution with fixture data."""
        fixture = fixture_loader.load("conversations_list")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        api = OpenHandsAPI("fake-api-key", "https://app.all-hands.dev/api/")

        # Test resolving by partial ID (first 8 chars of first conversation)
        result = resolve_conversation_id(api, "d2bfa2e2")
        assert result == "d2bfa2e22a0e4fef98882ab95258d4af"

    @responses.activate
    def test_resolve_conversation_id_number_out_of_range_with_fixtures(
        self, fixture_loader, capsys
    ):
        """Test number out of range with fixture data."""
        fixture = fixture_loader.load("conversations_list")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        api = OpenHandsAPI("fake-api-key", "https://app.all-hands.dev/api/")

        # Test with number beyond available conversations (fixture has 5)
        result = resolve_conversation_id(api, "10")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Conversation number 10 is out of range (1-5)" in captured.err

    def test_with_server_config_decorator_integration(self):
        """Test @with_server_config decorator with mocked config."""
        mock_config_manager = Mock()
        mock_config_manager.get_server_config.return_value = {
            "api_key": "test-integration-key",
            "url": "https://test-integration.example.com/api/",
        }

        @with_server_config
        def test_integration_command(api: OpenHandsAPI, server: str = None) -> dict:
            return {
                "api_base_url": api.base_url,
                "api_key": api.api_key,
                "server": server,
            }

        with patch("ohc.command_utils.ConfigManager", return_value=mock_config_manager):
            result = test_integration_command(server="integration-server")

        expected = {
            "api_base_url": "https://test-integration.example.com/api/",
            "api_key": "test-integration-key",
            "server": "integration-server",
        }
        assert result == expected
        mock_config_manager.get_server_config.assert_called_once_with(
            "integration-server"
        )

    @responses.activate
    def test_decorator_with_api_call_using_fixtures(self, fixture_loader):
        """Test decorator with actual API call using fixtures."""
        # Setup fixture response
        fixture = fixture_loader.load("conversations_list")
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=fixture["response"]["json"],
            status=fixture["response"]["status_code"],
        )

        # Mock config manager
        mock_config_manager = Mock()
        mock_config_manager.get_server_config.return_value = {
            "api_key": "fake-api-key",
            "url": "https://app.all-hands.dev/api/",
        }

        @with_server_config
        def test_api_command(api: OpenHandsAPI, server: str = None) -> dict:
            # Make an actual API call through the decorator-provided API instance
            result = api.search_conversations(limit=5)
            return {
                "conversation_count": len(result.get("results", [])),
                "first_conversation_id": result.get("results", [{}])[0].get(
                    "conversation_id"
                ),
            }

        with patch("ohc.command_utils.ConfigManager", return_value=mock_config_manager):
            result = test_api_command()

        assert result["conversation_count"] == 5
        assert result["first_conversation_id"] == "d2bfa2e22a0e4fef98882ab95258d4af"

    @responses.activate
    def test_resolve_conversation_id_with_multiple_partial_matches(
        self, fixture_loader, capsys
    ):
        """Test partial ID resolution with multiple matches using modified fixture data."""
        # Create modified fixture data with conversations that have common prefixes
        modified_response = {
            "results": [
                {"conversation_id": "abc123def456", "title": "Test Conv 1"},
                {"conversation_id": "abc456ghi789", "title": "Test Conv 2"},
                {"conversation_id": "def789xyz123", "title": "Test Conv 3"},
            ]
        }

        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/conversations",
            json=modified_response,
            status=200,
        )

        api = OpenHandsAPI("fake-api-key", "https://app.all-hands.dev/api/")

        # Test with partial ID that matches multiple conversations
        result = resolve_conversation_id(api, "abc")

        assert result is None
        captured = capsys.readouterr()
        assert "✗ Multiple conversations match 'abc'" in captured.err
        # Should show the matching conversations
        assert "abc123def456 - Test Conv 1" in captured.out
        assert "abc456ghi789 - Test Conv 2" in captured.out

    def test_full_conversation_id_passthrough(self):
        """Test that full conversation IDs are passed through without API calls."""
        api = OpenHandsAPI("fake-api-key", "https://app.all-hands.dev/api/")

        full_id = "d2bfa2e2-2a0e-4fef-9888-2ab95258d4af"  # 36 characters with hyphens
        result = resolve_conversation_id(api, full_id)

        assert result == full_id
        # Verify no API calls were made (responses would fail if any were made)
