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

from ohc.v1.api import OpenHandsAPI, SandboxNotRunningError


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

            with open(fixture_file) as f:
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

    @responses.activate
    def test_create_conversation(self, api_client, load_v1_fixture):
        """Test conversation creation with v1 API."""
        fixture = load_v1_fixture("conversation_create")

        responses.add(
            responses.POST,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        result = api_client.create_conversation()

        assert result["status"] == "ok"
        assert "conversation_id" in result
        assert result["conversation_id"] == "a1b2c3d4e5f6789012345678901234ab"

    def test_unimplemented_methods(self, api_client):
        """Test that unimplemented compatibility methods raise NotImplementedError."""
        # start_conversation still not implemented
        with pytest.raises(NotImplementedError):
            api_client.start_conversation({})


class TestV1SandboxAPI:
    """Tests for V1 sandbox-related API methods."""

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

            with open(fixture_file) as f:
                return json.load(f)

        return _load_fixture

    @pytest.fixture
    def api_client(self) -> OpenHandsAPI:
        """Create an OpenHands v1 API client for testing."""
        return OpenHandsAPI("test_api_key", "https://app.all-hands.dev/api/")

    @responses.activate
    def test_get_sandbox_info(self, api_client, load_v1_fixture):
        """Test getting sandbox info."""
        fixture = load_v1_fixture("sandbox_info")

        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        sandbox = api_client.get_sandbox_info("SANDBOX_ID_001")

        assert sandbox["id"] == "SANDBOX_ID_001"
        assert sandbox["status"] == "RUNNING"
        assert sandbox["session_api_key"] == "SESSION_API_KEY_001"
        assert "AGENT_SERVER" in sandbox["exposed_urls"]
        assert "VSCODE" in sandbox["exposed_urls"]

    @responses.activate
    def test_get_sandbox_info_not_found(self, api_client):
        """Test getting sandbox info when sandbox doesn't exist."""
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/v1/sandboxes",
            json={"error": "Not found"},
            status=404,
        )

        with pytest.raises(ValueError) as exc_info:
            api_client.get_sandbox_info("nonexistent")

        assert "Sandbox not found" in str(exc_info.value)

    @responses.activate
    def test_get_conversation(self, api_client, load_v1_fixture):
        """Test getting conversation by ID."""
        fixture = load_v1_fixture("conversation_get")

        responses.add(
            responses.GET,
            fixture["url"],
            json=fixture["json"],
            status=fixture["status_code"],
        )

        conv = api_client.get_conversation("CONV_ID_001")

        assert conv is not None
        assert conv["id"] == "CONV_ID_001"
        assert conv["title"] == "Test V1 Conversation"
        assert conv["status"] == "RUNNING"
        assert conv["sandbox_id"] == "SANDBOX_ID_001"

    @responses.activate
    def test_get_conversation_not_found(self, api_client):
        """Test getting conversation that doesn't exist."""
        responses.add(
            responses.GET,
            "https://app.all-hands.dev/api/v1/app-conversations",
            json={"error": "Not found"},
            status=404,
        )

        result = api_client.get_conversation("nonexistent")
        assert result is None


class TestV1AgentServerAPI:
    """Tests for V1 Agent Server API methods (file, git, trajectory)."""

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

            with open(fixture_file) as f:
                return json.load(f)

        return _load_fixture

    @pytest.fixture
    def api_client(self) -> OpenHandsAPI:
        """Create an OpenHands v1 API client for testing."""
        return OpenHandsAPI("test_api_key", "https://app.all-hands.dev/api/")

    def _setup_conversation_and_sandbox(self, load_v1_fixture):
        """Helper to set up conversation and sandbox responses."""
        conv_fixture = load_v1_fixture("conversation_get")
        sandbox_fixture = load_v1_fixture("sandbox_info")

        responses.add(
            responses.GET,
            conv_fixture["url"],
            json=conv_fixture["json"],
            status=conv_fixture["status_code"],
        )
        responses.add(
            responses.GET,
            sandbox_fixture["url"],
            json=sandbox_fixture["json"],
            status=sandbox_fixture["status_code"],
        )

    @responses.activate
    def test_get_conversation_changes(self, api_client, load_v1_fixture):
        """Test getting git changes from Agent Server."""
        self._setup_conversation_and_sandbox(load_v1_fixture)

        git_fixture = load_v1_fixture("git_changes")
        responses.add(
            responses.GET,
            git_fixture["url"],
            json=git_fixture["json"],
            status=git_fixture["status_code"],
        )

        changes = api_client.get_conversation_changes("CONV_ID_001")

        assert changes is not None
        assert len(changes) == 3
        assert changes[0]["path"] == "src/main.py"
        assert changes[0]["status"] == "modified"
        assert changes[2]["status"] == "added"

    @responses.activate
    def test_get_conversation_changes_sandbox_paused(self, api_client, load_v1_fixture):
        """Test getting git changes when sandbox is paused."""
        conv_fixture = load_v1_fixture("conversation_get")
        sandbox_fixture = load_v1_fixture("sandbox_paused")

        # Override the sandbox_id in the conversation fixture
        conv_json = conv_fixture["json"].copy()
        conv_json["sandbox_id"] = "SANDBOX_ID_PAUSED"

        responses.add(
            responses.GET,
            conv_fixture["url"],
            json=conv_json,
            status=conv_fixture["status_code"],
        )
        responses.add(
            responses.GET,
            sandbox_fixture["url"],
            json=sandbox_fixture["json"],
            status=sandbox_fixture["status_code"],
        )

        with pytest.raises(SandboxNotRunningError) as exc_info:
            api_client.get_conversation_changes("CONV_ID_001")

        assert exc_info.value.status == "PAUSED"
        assert "SANDBOX_ID_PAUSED" in str(exc_info.value)

    @responses.activate
    def test_get_file_content(self, api_client, load_v1_fixture):
        """Test downloading file content from Agent Server."""
        self._setup_conversation_and_sandbox(load_v1_fixture)

        file_fixture = load_v1_fixture("file_download")
        responses.add(
            responses.GET,
            file_fixture["url"],
            body=file_fixture["text"],
            status=file_fixture["status_code"],
            headers=file_fixture["headers"],
        )

        content = api_client.get_file_content("CONV_ID_001", "README.md")

        assert content is not None
        assert "# Test Project" in content
        assert "pytest" in content

    @responses.activate
    def test_get_file_content_not_found(self, api_client, load_v1_fixture):
        """Test downloading file that doesn't exist."""
        self._setup_conversation_and_sandbox(load_v1_fixture)

        responses.add(
            responses.GET,
            "https://AGENT_SERVER_HOST.runtime.all-hands.dev/api/file/download/nonexistent.txt",
            json={"error": "Not found"},
            status=404,
        )

        content = api_client.get_file_content("CONV_ID_001", "nonexistent.txt")
        assert content is None

    @responses.activate
    def test_get_trajectory(self, api_client, load_v1_fixture):
        """Test downloading trajectory from Agent Server."""
        self._setup_conversation_and_sandbox(load_v1_fixture)

        traj_fixture = load_v1_fixture("trajectory_download")
        responses.add(
            responses.GET,
            traj_fixture["url"],
            json=traj_fixture["json"],
            status=traj_fixture["status_code"],
        )

        trajectory = api_client.get_trajectory("CONV_ID_001")

        assert trajectory is not None
        assert len(trajectory) == 3
        assert trajectory[0]["type"] == "action"
        assert trajectory[0]["action"] == "run"
        assert trajectory[2]["action"] == "finish"

    @responses.activate
    def test_get_trajectory_not_found(self, api_client, load_v1_fixture):
        """Test downloading trajectory that doesn't exist."""
        self._setup_conversation_and_sandbox(load_v1_fixture)

        responses.add(
            responses.GET,
            "https://AGENT_SERVER_HOST.runtime.all-hands.dev/api/file/download-trajectory/CONV_ID_001",
            json={"error": "Not found"},
            status=404,
        )

        trajectory = api_client.get_trajectory("CONV_ID_001")
        assert trajectory is None

    @responses.activate
    def test_download_workspace_archive(self, api_client, load_v1_fixture):
        """Test downloading workspace archive via bash zip + file download."""
        import re
        self._setup_conversation_and_sandbox(load_v1_fixture)

        # Mock the bash command to create the zip
        bash_fixture = load_v1_fixture("bash_zip_workspace")
        responses.add(
            responses.POST,
            bash_fixture["url"],
            json=bash_fixture["json"],
            status=bash_fixture["status_code"],
        )

        # Mock the zip file download - use callback to match any temp zip path
        # The URL is case-insensitive in the host portion
        def download_callback(request):
            return (200, {"content-type": "application/octet-stream"}, b"PK\x03\x04fake-zip-content")

        responses.add_callback(
            responses.GET,
            re.compile(r".*\.runtime\.all-hands\.dev/api/file/download/tmp/workspace-.*\.zip", re.IGNORECASE),
            callback=download_callback,
        )

        # Mock the cleanup command (ignore result)
        responses.add(
            responses.POST,
            bash_fixture["url"],
            json={"exit_code": 0, "stdout": "", "stderr": ""},
            status=200,
        )

        archive = api_client.download_workspace_archive("CONV_ID_001")

        assert archive is not None
        assert archive.startswith(b"PK")  # ZIP file magic bytes

    @responses.activate
    def test_download_workspace_archive_zip_failure(self, api_client, load_v1_fixture):
        """Test workspace archive download when zip creation fails."""
        self._setup_conversation_and_sandbox(load_v1_fixture)

        # Mock the bash command to fail
        responses.add(
            responses.POST,
            "https://AGENT_SERVER_HOST.runtime.all-hands.dev/api/bash/execute_bash_command",
            json={"exit_code": 1, "stdout": "", "stderr": "zip: command not found"},
            status=200,
        )

        with pytest.raises(Exception) as exc_info:
            api_client.download_workspace_archive("CONV_ID_001")

        assert "Failed to create workspace archive" in str(exc_info.value)
