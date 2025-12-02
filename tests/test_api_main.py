"""
Tests for the main API module with version selection.
"""

import pytest

from ohc.api import OpenHandsAPI, create_api_client


class TestOpenHandsAPIMain:
    """Tests for the main OpenHands API wrapper."""

    def test_create_v0_client(self):
        """Test creating a v0 API client."""
        api = create_api_client("test_key", "https://test.com/api/", "v0")
        assert api.version == "v0"
        assert api.api_key == "test_key"
        assert api.base_url == "https://test.com/api/"

    def test_create_v1_client(self):
        """Test creating a v1 API client."""
        api = create_api_client("test_key", "https://test.com/api/", "v1")
        assert api.version == "v1"
        assert api.api_key == "test_key"
        assert api.base_url == "https://test.com/api/"

    def test_invalid_version(self):
        """Test creating client with invalid version."""
        with pytest.raises(ValueError, match="Unsupported API version: v2"):
            create_api_client("test_key", "https://test.com/api/", "v2")

    def test_default_version(self):
        """Test that default version is v0."""
        api = OpenHandsAPI("test_key", "https://test.com/api/")
        assert api.version == "v0"

    def test_v1_specific_methods_with_v0(self):
        """Test that v1-specific methods raise AttributeError with v0 client."""
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        with pytest.raises(
            AttributeError, match="search_events is only available in v1 API"
        ):
            api.search_events()

        with pytest.raises(
            AttributeError, match="get_events_count is only available in v1 API"
        ):
            api.get_events_count()

        with pytest.raises(
            AttributeError, match="create_event is only available in v1 API"
        ):
            api.create_event({})

        with pytest.raises(
            AttributeError, match="search_app_conversations is only available in v1 API"
        ):
            api.search_app_conversations()

        with pytest.raises(
            AttributeError,
            match="get_app_conversations_count is only available in v1 API",
        ):
            api.get_app_conversations_count()

    def test_v1_specific_methods_with_v1(self):
        """Test that v1-specific methods are available with v1 client."""
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        # These should not raise AttributeError (though they may raise other errors)
        # We're just testing that the methods exist and are callable
        assert hasattr(api, "search_events")
        assert hasattr(api, "get_events_count")
        assert hasattr(api, "create_event")
        assert hasattr(api, "search_app_conversations")
        assert hasattr(api, "get_app_conversations_count")

    def test_common_methods_available_both_versions(self):
        """Test that common methods are available in both versions."""
        for version in ["v0", "v1"]:
            api = OpenHandsAPI("test_key", "https://test.com/api/", version)

            # These methods should be available in both versions
            assert hasattr(api, "test_connection")
            assert hasattr(api, "search_conversations")
            assert hasattr(api, "get_conversation")
            assert hasattr(api, "start_conversation")
            assert hasattr(api, "get_conversation_changes")
            assert hasattr(api, "get_file_content")
            assert hasattr(api, "download_workspace_archive")
            assert hasattr(api, "get_trajectory")

    def test_client_property(self):
        """Test that the client property returns the underlying API client."""
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")
        client = api.client

        # Should be the underlying v0 API client
        from ohc.v0.api import OpenHandsAPI as V0API

        assert isinstance(client, V0API)

        api_v1 = OpenHandsAPI("test_key", "https://test.com/api/", "v1")
        client_v1 = api_v1.client

        # Should be the underlying v1 API client
        from ohc.v1.api import OpenHandsAPI as V1API

        assert isinstance(client_v1, V1API)
