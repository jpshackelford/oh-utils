"""
Tests for the main API module with version selection.
"""

from unittest.mock import patch

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
            assert hasattr(api, "create_conversation")
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


class TestOpenHandsAPIMethodDelegation:
    """Tests for method delegation and version-specific behavior."""

    @patch("ohc.v0.api.OpenHandsAPI.test_connection")
    def test_test_connection_v0(self, mock_test_connection):
        """Test that test_connection delegates to v0 API correctly."""
        mock_test_connection.return_value = True
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.test_connection()

        assert result is True
        mock_test_connection.assert_called_once()

    @patch("ohc.v1.api.OpenHandsAPI.test_connection")
    def test_test_connection_v1(self, mock_test_connection):
        """Test that test_connection delegates to v1 API correctly."""
        mock_test_connection.return_value = False
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.test_connection()

        assert result is False
        mock_test_connection.assert_called_once()

    @patch("ohc.v0.api.OpenHandsAPI.search_conversations")
    def test_search_conversations_v0(self, mock_search):
        """Test search_conversations with v0 API - ignores query and offset."""
        mock_search.return_value = {"results": ["conv1", "conv2"]}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.search_conversations(query="test", limit=5, offset=10)

        # v0 should ignore query and offset, only pass limit
        mock_search.assert_called_once_with(limit=5)
        assert result == {"results": ["conv1", "conv2"]}

    @patch("ohc.v1.api.OpenHandsAPI.search_conversations")
    def test_search_conversations_v1(self, mock_search):
        """Test search_conversations with v1 API - uses all parameters."""
        mock_search.return_value = ["conv1", "conv2"]
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.search_conversations(query="test", limit=5, offset=10)

        # v1 should use all parameters and wrap results in dict
        mock_search.assert_called_once_with(query="test", limit=5, offset=10)
        assert result == {"results": ["conv1", "conv2"]}

    @patch("ohc.v0.api.OpenHandsAPI.get_conversation")
    def test_get_conversation_v0(self, mock_get):
        """Test get_conversation delegates to v0 API correctly."""
        mock_get.return_value = {"id": "conv123", "title": "Test"}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_conversation("conv123")

        mock_get.assert_called_once_with("conv123")
        assert result == {"id": "conv123", "title": "Test"}

    @patch("ohc.v1.api.OpenHandsAPI.get_conversation")
    def test_get_conversation_v1(self, mock_get):
        """Test get_conversation delegates to v1 API correctly."""
        mock_get.return_value = {"id": "conv123", "title": "Test"}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_conversation("conv123")

        mock_get.assert_called_once_with("conv123")
        assert result == {"id": "conv123", "title": "Test"}

    @patch("ohc.v0.api.OpenHandsAPI.create_conversation")
    def test_create_conversation_v0(self, mock_create):
        """Test create_conversation delegates to v0 API correctly."""
        mock_create.return_value = {
            "status": "ok",
            "conversation_id": "conv123",
            "conversation_status": "STOPPED",
        }
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.create_conversation()

        mock_create.assert_called_once_with()
        assert result["status"] == "ok"
        assert result["conversation_id"] == "conv123"

    @patch("ohc.v1.api.OpenHandsAPI.create_conversation")
    def test_create_conversation_v1(self, mock_create):
        """Test create_conversation delegates to v1 API correctly."""
        mock_create.return_value = {
            "status": "ok",
            "conversation_id": "conv123",
            "conversation_status": "STOPPED",
        }
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.create_conversation()

        mock_create.assert_called_once_with()
        assert result["status"] == "ok"
        assert result["conversation_id"] == "conv123"

    @patch("ohc.v0.api.OpenHandsAPI.start_conversation")
    def test_start_conversation_v0_success(self, mock_start):
        """Test start_conversation with v0 API - extracts conversation_id."""
        mock_start.return_value = {"id": "conv123", "status": "started"}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.start_conversation({"conversation_id": "conv123", "title": "Test"})

        mock_start.assert_called_once_with("conv123")
        assert result == {"id": "conv123", "status": "started"}

    def test_start_conversation_v0_missing_id(self):
        """Test start_conversation with v0 API raises error when conversation_id missing."""
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        with pytest.raises(ValueError, match="conversation_id is required for v0 API"):
            api.start_conversation({"title": "Test"})

    def test_start_conversation_v0_empty_id(self):
        """Test start_conversation with v0 API raises error when conversation_id is empty."""
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        with pytest.raises(ValueError, match="conversation_id is required for v0 API"):
            api.start_conversation({"conversation_id": "", "title": "Test"})

    @patch("ohc.v1.api.OpenHandsAPI.start_conversation")
    def test_start_conversation_v1(self, mock_start):
        """Test start_conversation with v1 API - passes full data dict."""
        mock_start.return_value = {"id": "conv123", "status": "started"}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")
        conversation_data = {"title": "Test", "description": "Test conversation"}

        result = api.start_conversation(conversation_data)

        mock_start.assert_called_once_with(conversation_data)
        assert result == {"id": "conv123", "status": "started"}

    @patch("ohc.v0.api.OpenHandsAPI.get_conversation_changes")
    def test_get_conversation_changes_v0(self, mock_get_changes):
        """Test get_conversation_changes with v0 API - includes session_api_key."""
        mock_get_changes.return_value = [{"file": "test.py", "status": "modified"}]
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_conversation_changes(
            "conv123", "http://runtime", "session_key"
        )

        mock_get_changes.assert_called_once_with(
            "conv123", "http://runtime", "session_key"
        )
        assert result == [{"file": "test.py", "status": "modified"}]

    @patch("ohc.v1.api.OpenHandsAPI.get_conversation_changes")
    def test_get_conversation_changes_v1_with_changes(self, mock_get_changes):
        """Test get_conversation_changes with v1 API - extracts changes from result."""
        mock_get_changes.return_value = {
            "changes": [{"file": "test.py", "status": "modified"}]
        }
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_conversation_changes("conv123", "http://runtime")

        mock_get_changes.assert_called_once_with("conv123", "http://runtime")
        assert result == [{"file": "test.py", "status": "modified"}]

    @patch("ohc.v1.api.OpenHandsAPI.get_conversation_changes")
    def test_get_conversation_changes_v1_no_changes(self, mock_get_changes):
        """Test get_conversation_changes with v1 API - handles missing changes key."""
        mock_get_changes.return_value = {"status": "no_changes"}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_conversation_changes("conv123", "http://runtime")

        mock_get_changes.assert_called_once_with("conv123", "http://runtime")
        assert result is None

    @patch("ohc.v1.api.OpenHandsAPI.get_conversation_changes")
    def test_get_conversation_changes_v1_none_result(self, mock_get_changes):
        """Test get_conversation_changes with v1 API - handles None result."""
        mock_get_changes.return_value = None
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_conversation_changes("conv123", "http://runtime")

        mock_get_changes.assert_called_once_with("conv123", "http://runtime")
        assert result is None

    @patch("ohc.v0.api.OpenHandsAPI.get_file_content")
    def test_get_file_content_v0(self, mock_get_file):
        """Test get_file_content with v0 API - includes session_api_key."""
        mock_get_file.return_value = "file content"
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_file_content(
            "conv123", "test.py", "http://runtime", "session_key"
        )

        mock_get_file.assert_called_once_with(
            "conv123", "test.py", "http://runtime", "session_key"
        )
        assert result == "file content"

    @patch("ohc.v1.api.OpenHandsAPI.get_file_content")
    def test_get_file_content_v1(self, mock_get_file):
        """Test get_file_content with v1 API - no session_api_key."""
        mock_get_file.return_value = "file content"
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_file_content("conv123", "test.py", "http://runtime")

        mock_get_file.assert_called_once_with("conv123", "test.py", "http://runtime")
        assert result == "file content"

    @patch("ohc.v0.api.OpenHandsAPI.download_workspace_archive")
    def test_download_workspace_archive_v0(self, mock_download):
        """Test download_workspace_archive with v0 API - includes session_api_key."""
        mock_download.return_value = b"archive content"
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.download_workspace_archive(
            "conv123", "http://runtime", "session_key"
        )

        mock_download.assert_called_once_with(
            "conv123", "http://runtime", "session_key"
        )
        assert result == b"archive content"

    @patch("ohc.v1.api.OpenHandsAPI.download_workspace_archive")
    def test_download_workspace_archive_v1(self, mock_download):
        """Test download_workspace_archive with v1 API - no session_api_key."""
        mock_download.return_value = b"archive content"
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.download_workspace_archive("conv123", "http://runtime")

        mock_download.assert_called_once_with("conv123", "http://runtime")
        assert result == b"archive content"

    @patch("ohc.v0.api.OpenHandsAPI.get_trajectory")
    def test_get_trajectory_v0_success(self, mock_get_trajectory):
        """Test get_trajectory with v0 API - extracts trajectory from dict result."""
        mock_get_trajectory.return_value = {"trajectory": [{"step": 1}, {"step": 2}]}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_trajectory("conv123", "http://runtime", "session_key")

        mock_get_trajectory.assert_called_once_with(
            "conv123", "http://runtime", "session_key"
        )
        assert result == [{"step": 1}, {"step": 2}]

    @patch("ohc.v0.api.OpenHandsAPI.get_trajectory")
    def test_get_trajectory_v0_no_runtime_url(self, mock_get_trajectory):
        """Test get_trajectory with v0 API - returns None when no runtime_url."""
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_trajectory("conv123", None, "session_key")

        mock_get_trajectory.assert_not_called()
        assert result is None

    @patch("ohc.v0.api.OpenHandsAPI.get_trajectory")
    def test_get_trajectory_v0_no_trajectory_key(self, mock_get_trajectory):
        """Test get_trajectory with v0 API - handles missing trajectory key."""
        mock_get_trajectory.return_value = {"status": "no_trajectory"}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_trajectory("conv123", "http://runtime", "session_key")

        mock_get_trajectory.assert_called_once_with(
            "conv123", "http://runtime", "session_key"
        )
        assert result is None

    @patch("ohc.v0.api.OpenHandsAPI.get_trajectory")
    def test_get_trajectory_v0_uses_api_key_as_default_session_key(
        self, mock_get_trajectory
    ):
        """Test get_trajectory with v0 API - uses api_key when session_api_key is None."""
        mock_get_trajectory.return_value = {"trajectory": [{"step": 1}]}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v0")

        result = api.get_trajectory("conv123", "http://runtime", None)

        mock_get_trajectory.assert_called_once_with(
            "conv123", "http://runtime", "test_key"
        )
        assert result == [{"step": 1}]

    @patch("ohc.v1.api.OpenHandsAPI.get_trajectory")
    def test_get_trajectory_v1(self, mock_get_trajectory):
        """Test get_trajectory with v1 API - direct delegation."""
        mock_get_trajectory.return_value = [{"step": 1}, {"step": 2}]
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_trajectory("conv123", "http://runtime")

        mock_get_trajectory.assert_called_once_with("conv123", "http://runtime")
        assert result == [{"step": 1}, {"step": 2}]


class TestOpenHandsAPIV1SpecificMethods:
    """Tests for v1-specific method implementations."""

    @patch("ohc.v1.api.OpenHandsAPI.search_events")
    def test_search_events_v1_implementation(self, mock_search_events):
        """Test search_events actually calls v1 API with correct parameters."""
        mock_search_events.return_value = [{"event": "test"}]
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.search_events(
            query="test",
            limit=5,
            offset=10,
            event_type="action",
            conversation_id="conv123",
        )

        mock_search_events.assert_called_once_with(
            query="test",
            limit=5,
            offset=10,
            event_type="action",
            conversation_id="conv123",
        )
        assert result == [{"event": "test"}]

    @patch("ohc.v1.api.OpenHandsAPI.get_events_count")
    def test_get_events_count_v1_implementation(self, mock_get_count):
        """Test get_events_count actually calls v1 API with correct parameters."""
        mock_get_count.return_value = 42
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_events_count(
            query="test", event_type="action", conversation_id="conv123"
        )

        mock_get_count.assert_called_once_with(
            query="test", event_type="action", conversation_id="conv123"
        )
        assert result == 42

    @patch("ohc.v1.api.OpenHandsAPI.create_event")
    def test_create_event_v1_implementation(self, mock_create_event):
        """Test create_event actually calls v1 API with correct parameters."""
        event_data = {"type": "action", "data": {"command": "test"}}
        mock_create_event.return_value = {"id": "event123", **event_data}
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.create_event(event_data)

        mock_create_event.assert_called_once_with(event_data)
        assert result == {"id": "event123", **event_data}

    @patch("ohc.v1.api.OpenHandsAPI.search_app_conversations")
    def test_search_app_conversations_v1_implementation(self, mock_search_app):
        """Test search_app_conversations actually calls v1 API with correct parameters."""
        mock_search_app.return_value = [{"app_conv": "test"}]
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.search_app_conversations(
            query="test", limit=5, offset=10, status="active"
        )

        mock_search_app.assert_called_once_with(
            query="test", limit=5, offset=10, status="active"
        )
        assert result == [{"app_conv": "test"}]

    @patch("ohc.v1.api.OpenHandsAPI.get_app_conversations_count")
    def test_get_app_conversations_count_v1_implementation(self, mock_get_count):
        """Test get_app_conversations_count actually calls v1 API with correct parameters."""
        mock_get_count.return_value = 15
        api = OpenHandsAPI("test_key", "https://test.com/api/", "v1")

        result = api.get_app_conversations_count(query="test", status="active")

        mock_get_count.assert_called_once_with(query="test", status="active")
        assert result == 15


class TestCreateAPIClientFactory:
    """Tests for the create_api_client factory function."""

    def test_create_api_client_defaults(self):
        """Test create_api_client with default parameters."""
        api = create_api_client("test_key")

        assert api.api_key == "test_key"
        assert api.base_url == "https://app.all-hands.dev/api/"
        assert api.version == "v0"

    def test_create_api_client_custom_params(self):
        """Test create_api_client with custom parameters."""
        api = create_api_client("test_key", "https://custom.com/api/", "v1")

        assert api.api_key == "test_key"
        assert api.base_url == "https://custom.com/api/"
        assert api.version == "v1"
