"""
Tests for URL handling fixes to ensure hardcoded URL assumptions are removed.

This test file specifically tests the fix for issue #10 where hardcoded URL
assumptions break with custom Kubernetes configurations.
"""

from urllib.parse import urljoin

import pytest
import responses

from ohc.api import OpenHandsAPI
from ohc.conversation_display import Conversation


class TestURLHandling:
    """Test URL handling without hardcoded assumptions."""

    @pytest.fixture
    def api_client(self) -> OpenHandsAPI:
        """Create an API client instance for testing."""
        return OpenHandsAPI(
            api_key="fake-api-key", base_url="https://app.all-hands.dev/api/"
        )

    def test_conversation_from_api_response_with_custom_domain(self):
        """Test that Conversation.from_api_response works with custom domains."""
        # Test with custom domain (not prod-runtime.all-hands.dev)
        custom_url = "https://runtime-123.custom-k8s.example.com/workspace"
        api_data = {
            "conversation_id": "conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "active",
            "session_api_key": "sess_fake123",
            "last_updated_at": "2023-01-01T00:00:00Z",
            "created_at": "2023-01-01T00:00:00Z",
            "url": custom_url,
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "conv-123"
        assert conv.title == "Test Conversation"
        assert conv.status == "RUNNING"
        assert conv.url == custom_url
        # Runtime ID should be extracted from hostname for display purposes
        assert conv.runtime_id == "runtime-123"

    def test_conversation_from_api_response_with_different_url_patterns(self):
        """Test that runtime ID extraction works with various URL patterns."""
        test_cases = [
            # Standard prod-runtime pattern
            {
                "url": "https://work-1-abc123.prod-runtime.all-hands.dev/workspace",
                "expected_runtime_id": "work-1-abc123",
            },
            # Custom domain with different pattern
            {
                "url": "https://runtime-xyz.internal.company.com/api",
                "expected_runtime_id": "runtime-xyz",
            },
            # Different subdomain structure
            {
                "url": "https://session-456.k8s-cluster.example.org/",
                "expected_runtime_id": "session-456",
            },
            # IP address (should extract first part)
            {
                "url": "https://192.168.1.100:8080/workspace",
                "expected_runtime_id": "192",
            },
        ]

        for case in test_cases:
            api_data = {
                "conversation_id": "conv-123",
                "title": "Test",
                "status": "RUNNING",
                "url": case["url"],
            }

            conv = Conversation.from_api_response(api_data)
            assert conv.runtime_id == case["expected_runtime_id"]
            assert conv.url == case["url"]

    def test_conversation_from_api_response_with_invalid_url(self):
        """Test that invalid URLs don't break the parsing."""
        test_cases = [
            {"url": "not-a-url", "expected_runtime_id": None},
            {"url": "", "expected_runtime_id": None},
            {"url": None, "expected_runtime_id": None},
            {
                "url": "ftp://invalid-protocol.com",
                "expected_runtime_id": "invalid-protocol",
            },  # This actually parses correctly
        ]

        for case in test_cases:
            api_data = {
                "conversation_id": "conv-123",
                "title": "Test",
                "status": "RUNNING",
                "url": case["url"],
            }

            conv = Conversation.from_api_response(api_data)
            # Should not crash and runtime_id should match expected
            assert conv.runtime_id == case["expected_runtime_id"]
            assert conv.url == case["url"]

    @responses.activate
    def test_get_conversation_changes_with_custom_runtime_url(self, api_client):
        """Test get_conversation_changes works with custom runtime URLs."""
        conversation_id = "conv-123"
        custom_runtime_url = "https://runtime-abc.custom-k8s.example.com"
        session_api_key = "sess_fake123"

        # Mock the API response
        expected_url = urljoin(
            custom_runtime_url, f"api/conversations/{conversation_id}/git/changes"
        )
        responses.add(
            responses.GET,
            expected_url,
            json=[
                {"path": "test.py", "status": "M"},
                {"path": "new_file.py", "status": "A"},
            ],
            status=200,
        )

        result = api_client.get_conversation_changes(
            conversation_id, custom_runtime_url, session_api_key
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["path"] == "test.py"
        assert result[0]["status"] == "M"

    @responses.activate
    def test_get_file_content_with_custom_runtime_url(self, api_client):
        """Test get_file_content works with custom runtime URLs."""
        conversation_id = "conv-123"
        file_path = "example.py"
        custom_runtime_url = "https://runtime-xyz.internal.company.com"
        session_api_key = "sess_fake123"

        # Mock the API response
        expected_url = urljoin(
            custom_runtime_url, f"api/conversations/{conversation_id}/select-file"
        )
        responses.add(
            responses.GET,
            expected_url,
            json={"code": "print('Hello from custom runtime!')"},
            status=200,
        )

        result = api_client.get_file_content(
            conversation_id, file_path, custom_runtime_url, session_api_key
        )

        assert result == "print('Hello from custom runtime!')"

    @responses.activate
    def test_download_workspace_archive_with_custom_runtime_url(self, api_client):
        """Test download_workspace_archive works with custom runtime URLs."""
        conversation_id = "conv-123"
        custom_runtime_url = "https://session-456.k8s-cluster.example.org"
        session_api_key = "sess_fake123"
        fake_zip_content = b"PK\x03\x04custom zip content"

        # Mock the API response
        expected_url = urljoin(
            custom_runtime_url, f"api/conversations/{conversation_id}/zip-directory"
        )
        responses.add(
            responses.GET,
            expected_url,
            body=fake_zip_content,
            status=200,
            headers={"Content-Type": "application/zip"},
        )

        result = api_client.download_workspace_archive(
            conversation_id, custom_runtime_url, session_api_key
        )

        assert result == fake_zip_content

    @responses.activate
    def test_get_trajectory_with_custom_runtime_url(self, api_client):
        """Test get_trajectory works with custom runtime URLs."""
        conversation_id = "conv-123"
        custom_runtime_url = "https://runtime-789.enterprise.local"
        session_api_key = "sess_fake123"

        # Mock the API response
        expected_url = urljoin(
            custom_runtime_url, f"api/conversations/{conversation_id}/trajectory"
        )
        responses.add(
            responses.GET,
            expected_url,
            json={"trajectory": "fake trajectory data"},
            status=200,
        )

        result = api_client.get_trajectory(
            conversation_id, custom_runtime_url, session_api_key
        )

        assert isinstance(result, dict)
        assert result["trajectory"] == "fake trajectory data"

    @responses.activate
    def test_api_methods_work_without_runtime_url(self, api_client):
        """Test that API methods still work when no runtime URL is provided."""
        conversation_id = "conv-123"

        # Test get_conversation_changes fallback
        responses.add(
            responses.GET,
            f"https://app.all-hands.dev/api/conversations/{conversation_id}/git/changes",
            json=[],
            status=200,
        )

        result = api_client.get_conversation_changes(conversation_id, None, None)
        assert result == []

        # Test get_file_content fallback
        responses.add(
            responses.GET,
            f"https://app.all-hands.dev/api/conversations/{conversation_id}/select-file",
            json={"code": "fallback content"},
            status=200,
        )

        result = api_client.get_file_content(conversation_id, "test.py", None, None)
        assert result == "fallback content"

    def test_no_hardcoded_domain_references(self):
        """Test that no hardcoded domain references remain in the code."""
        # This is a meta-test to ensure we haven't missed any hardcoded references
        import inspect

        from conversation_manager import conversation_manager
        from ohc import api

        # Get source code of the modules
        api_source = inspect.getsource(api)
        cm_source = inspect.getsource(conversation_manager)

        # Check that hardcoded domain is not present in URL construction
        hardcoded_patterns = [
            "prod-runtime.all-hands.dev",
            'f"https://{runtime_id}.',  # Pattern for URL construction
            "runtime_id}.prod-runtime",  # Part of the old pattern
        ]

        for pattern in hardcoded_patterns:
            assert pattern not in api_source, (
                f"Found hardcoded pattern '{pattern}' in ohc.api"
            )
            assert pattern not in cm_source, (
                f"Found hardcoded pattern '{pattern}' in conversation_manager"
            )

    def test_url_parameter_names_updated(self):
        """Test that method signatures use runtime_url instead of runtime_id."""
        import inspect

        from ohc.api import OpenHandsAPI

        # Check that methods now accept runtime_url parameter
        methods_to_check = [
            "get_conversation_changes",
            "get_file_content",
            "download_workspace_archive",
            "get_trajectory",
        ]

        for method_name in methods_to_check:
            method = getattr(OpenHandsAPI, method_name)
            sig = inspect.signature(method)

            # Should have runtime_url parameter (not runtime_id)
            assert "runtime_url" in sig.parameters, (
                f"{method_name} should have runtime_url parameter"
            )

            # For get_trajectory, runtime_url should be required (not Optional)
            if method_name == "get_trajectory":
                param = sig.parameters["runtime_url"]
                # Check that it's not Optional by looking at the annotation
                assert "Optional" not in str(param.annotation), (
                    f"{method_name} runtime_url should not be Optional"
                )
