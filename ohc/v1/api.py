"""
OpenHands v1 API client for the ohc CLI.

This module implements the v1 API endpoints which use /v1 prefixes
and provide enhanced functionality for events and app-conversations.

V1 uses a two-tier API architecture:
- App Server (app.all-hands.dev/api/v1): Manages conversations and sandboxes
  - Uses `Authorization: Bearer {api_key}` header
- Agent Server (per-sandbox URL): Runtime/workspace operations
  - Uses `X-Session-API-Key: {session_api_key}` header
"""

import contextlib
import uuid
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urljoin

import requests


class SandboxNotRunningError(Exception):
    """Raised when a sandbox operation requires a running sandbox but it's not."""

    def __init__(self, sandbox_id: str, status: str, message: Optional[str] = None):
        self.sandbox_id = sandbox_id
        self.status = status
        default_msg = f"Sandbox {sandbox_id} is not running (status: {status})"
        self.message = message or default_msg
        super().__init__(self.message)


class OpenHandsAPI:
    """
    OpenHands v1 API client for conversation and event management.

    This client provides access to the v1 API endpoints which include
    enhanced event search, app-conversation management, and improved
    data structures.

    V1 uses a two-tier architecture:
    - App Server: Manages conversations and sandboxes (uses Authorization header)
    - Agent Server: Runtime operations on active sandboxes (uses X-Session-API-Key)

    Attributes:
        api_key: OpenHands API key for authentication
        base_url: Base URL for the OpenHands API endpoint
        session: Configured requests session with authentication headers
    """

    def __init__(self, api_key: str, base_url: str = "https://app.all-hands.dev/api/"):
        """
        Initialize the OpenHands v1 API client.

        Args:
            api_key: OpenHands API key from https://app.all-hands.dev/settings/api-keys
            base_url: Base URL for the API endpoint, defaults to production
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        # App Server uses Authorization: Bearer header
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )

    def test_connection(self) -> bool:
        """
        Test if the API key and URL are valid by checking v1 events endpoint.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, "v1/events/count"), timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def search_events(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        event_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search events using the v1 events API.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip
            event_type: Filter by event type
            conversation_id: Filter by conversation ID

        Returns:
            List of event dictionaries

        Raises:
            requests.HTTPError: If the API request fails
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            params["query"] = query
        if event_type:
            params["event_type"] = event_type
        if conversation_id:
            params["conversation_id"] = conversation_id

        response = self.session.get(
            urljoin(self.base_url, "v1/events/search"), params=params, timeout=30
        )

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)

        response.raise_for_status()
        return cast("List[Dict[str, Any]]", response.json())

    def get_events_count(
        self,
        query: Optional[str] = None,
        event_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> int:
        """
        Get count of events matching criteria.

        Args:
            query: Search query string
            event_type: Filter by event type
            conversation_id: Filter by conversation ID

        Returns:
            Number of matching events

        Raises:
            requests.HTTPError: If the API request fails
        """
        params = {}
        if query:
            params["query"] = query
        if event_type:
            params["event_type"] = event_type
        if conversation_id:
            params["conversation_id"] = conversation_id

        response = self.session.get(
            urljoin(self.base_url, "v1/events/count"), params=params, timeout=30
        )

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)

        response.raise_for_status()
        return cast("int", response.json().get("count", 0))

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new event using the v1 events API.

        Args:
            event_data: Event data dictionary

        Returns:
            Created event dictionary

        Raises:
            requests.HTTPError: If the API request fails
        """
        response = self.session.post(
            urljoin(self.base_url, "v1/events"), json=event_data, timeout=30
        )

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)

        response.raise_for_status()
        return cast("Dict[str, Any]", response.json())

    def search_app_conversations(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search app conversations using the v1 API.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip
            status: Filter by conversation status

        Returns:
            List of app conversation dictionaries

        Raises:
            requests.HTTPError: If the API request fails
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            params["query"] = query
        if status:
            params["status"] = status

        response = self.session.get(
            urljoin(self.base_url, "v1/app-conversations/search"),
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)

        response.raise_for_status()
        data = response.json()
        # Extract items from the response structure
        if isinstance(data, dict) and "items" in data:
            return cast("List[Dict[str, Any]]", data["items"])
        return cast("List[Dict[str, Any]]", data)

    def get_app_conversations_count(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        Get count of app conversations matching criteria.

        Args:
            query: Search query string
            status: Filter by conversation status

        Returns:
            Number of matching app conversations

        Raises:
            requests.HTTPError: If the API request fails
        """
        params = {}
        if query:
            params["query"] = query
        if status:
            params["status"] = status

        response = self.session.get(
            urljoin(self.base_url, "v1/app-conversations/count"),
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)

        response.raise_for_status()
        return cast("int", response.json().get("count", 0))

    def get_sandbox_info(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Get sandbox details including Agent Server URL and session API key.

        This is a core V1 API method that retrieves the information needed
        to make Agent Server calls for runtime operations.

        Args:
            sandbox_id: The sandbox identifier

        Returns:
            Dictionary containing sandbox info:
            - id: Sandbox ID
            - status: STARTING, RUNNING, PAUSED, ERROR, MISSING
            - session_api_key: Key for Agent Server authentication
            - exposed_urls: Dict with AGENT_SERVER, VSCODE URLs

        Raises:
            requests.HTTPError: If the API request fails
            ValueError: If sandbox not found
        """
        url = urljoin(self.base_url, "v1/sandboxes")
        params = {"id": sandbox_id}

        response = self.session.get(url, params=params, timeout=30)

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)
        if response.status_code == 404:
            raise ValueError(f"Sandbox not found: {sandbox_id}")

        response.raise_for_status()
        return cast("Dict[str, Any]", response.json())

    def _make_agent_server_request(
        self,
        agent_server_url: str,
        session_api_key: str,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> requests.Response:
        """
        Make a request to the Agent Server with proper authentication.

        The Agent Server runs on each active sandbox and provides direct access
        to workspace operations. It uses X-Session-API-Key for authentication.

        Args:
            agent_server_url: Base URL of Agent Server (from exposed_urls.AGENT_SERVER)
            session_api_key: Session API key (from sandbox.session_api_key)
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., '/api/git/changes/.')
            params: Optional query parameters
            json_data: Optional JSON body data
            timeout: Request timeout in seconds

        Returns:
            requests.Response object

        Raises:
            requests.HTTPError: If the request fails
        """
        url = urljoin(agent_server_url.rstrip("/") + "/", endpoint.lstrip("/"))
        headers = {"X-Session-API-Key": session_api_key}

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=timeout,
        )

        if response.status_code == 401:
            raise requests.HTTPError(
                "Agent Server authentication failed - invalid session API key",
                response=response,
            )

        return response

    def _get_agent_server_info(
        self, conversation_id: str
    ) -> tuple[str, str, Dict[str, Any]]:
        """
        Get Agent Server connection info for a conversation.

        This helper retrieves the conversation to get sandbox_id, then fetches
        sandbox info to get the Agent Server URL and session key.

        Args:
            conversation_id: Conversation ID

        Returns:
            Tuple of (agent_server_url, session_api_key, sandbox_info)

        Raises:
            SandboxNotRunningError: If sandbox is not in RUNNING status
            ValueError: If conversation or sandbox not found
        """
        # Get conversation to find sandbox_id
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        sandbox_id = conversation.get("sandbox_id")
        if not sandbox_id:
            raise ValueError(
                f"Conversation {conversation_id} has no associated sandbox"
            )

        # Get sandbox info for Agent Server access
        sandbox = self.get_sandbox_info(sandbox_id)
        status = sandbox.get("status", "UNKNOWN")

        if status != "RUNNING":
            raise SandboxNotRunningError(sandbox_id, status)

        agent_server_url = sandbox.get("exposed_urls", {}).get("AGENT_SERVER")
        if not agent_server_url:
            raise ValueError(f"Sandbox {sandbox_id} has no Agent Server URL available")

        session_api_key = sandbox.get("session_api_key")
        if not session_api_key:
            raise ValueError(f"Sandbox {sandbox_id} has no session API key available")

        return agent_server_url, session_api_key, sandbox

    # Legacy compatibility methods - these delegate to v0-style behavior
    # but use v1 endpoints where possible

    def search_conversations(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations (compatibility method using app-conversations).

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of conversation dictionaries

        Raises:
            requests.HTTPError: If the API request fails
        """
        return self.search_app_conversations(query=query, limit=limit, offset=offset)

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation details by ID.

        Uses the V1 app-conversations endpoint with id query parameter.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation dictionary or None if not found

        Raises:
            requests.HTTPError: If the API request fails
        """
        url = urljoin(self.base_url, "v1/app-conversations")
        params = {"id": conversation_id}

        response = self.session.get(url, params=params, timeout=30)

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)
        if response.status_code == 404:
            return None

        response.raise_for_status()
        return cast("Optional[Dict[str, Any]]", response.json())

    def create_conversation(self) -> Dict[str, Any]:
        """
        Create a new conversation using v1 API.

        Returns:
            Dictionary containing the new conversation details

        Raises:
            requests.HTTPError: If the API request fails
        """
        url = urljoin(self.base_url, "v1/app-conversations")

        try:
            response = self.session.post(url, json={"request": {}})
            response.raise_for_status()
            data = response.json()

            # Convert v1 response format to match v0 format for compatibility
            return {
                "status": "ok",
                "conversation_id": data.get("id"),
                "message": None,
                "conversation_status": data.get("status", "WORKING"),
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create conversation - {str(e)}") from e

    def start_conversation(
        self,
        conversation_id: str,
        providers_set: Optional[List[str]] = None,  # noqa: ARG002 - V0 compat
    ) -> Dict[str, Any]:
        """
        Start/wake up a conversation by resuming its sandbox.

        In V1, conversations and sandboxes are decoupled. This method:
        1. Gets the conversation to find its sandbox_id
        2. Checks the sandbox status
        3. Resumes the sandbox if it's paused

        Args:
            conversation_id: Conversation ID to start
            providers_set: Deprecated - V1 doesn't use providers_set

        Returns:
            Dictionary containing conversation and sandbox info

        Raises:
            ValueError: If conversation not found or has no sandbox
            requests.HTTPError: If the API request fails
        """
        # Get conversation to find sandbox_id
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        sandbox_id = conversation.get("sandbox_id")
        if not sandbox_id:
            raise ValueError(
                f"Conversation {conversation_id} has no associated sandbox"
            )

        # Get sandbox info
        sandbox = self.get_sandbox_info(sandbox_id)
        status = sandbox.get("status", "UNKNOWN")

        # If sandbox is paused, resume it
        if status == "PAUSED":
            self.resume_sandbox(sandbox_id)
            # Refresh sandbox info after resume
            sandbox = self.get_sandbox_info(sandbox_id)

        # Return combined info similar to V0 response format
        return {
            "status": "ok",
            "conversation_id": conversation_id,
            "sandbox_id": sandbox_id,
            "sandbox_status": sandbox.get("status"),
            "runtime_url": sandbox.get("exposed_urls", {}).get("AGENT_SERVER"),
            "session_api_key": sandbox.get("session_api_key"),
        }

    def resume_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Resume a paused sandbox.

        Args:
            sandbox_id: The sandbox identifier

        Returns:
            Response from the resume endpoint

        Raises:
            requests.HTTPError: If the API request fails
        """
        url = urljoin(self.base_url, f"v1/sandboxes/{sandbox_id}/resume")

        response = self.session.post(url, timeout=60)

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)
        if response.status_code == 404:
            raise ValueError(f"Sandbox not found: {sandbox_id}")

        response.raise_for_status()
        return cast("Dict[str, Any]", response.json())

    def pause_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Pause a running sandbox.

        Args:
            sandbox_id: The sandbox identifier

        Returns:
            Response from the pause endpoint

        Raises:
            requests.HTTPError: If the API request fails
        """
        url = urljoin(self.base_url, f"v1/sandboxes/{sandbox_id}/pause")

        response = self.session.post(url, timeout=30)

        if response.status_code == 401:
            raise requests.HTTPError("Unauthorized: Invalid API key", response=response)
        if response.status_code == 404:
            raise ValueError(f"Sandbox not found: {sandbox_id}")

        response.raise_for_status()
        return cast("Dict[str, Any]", response.json())

    def get_conversation_changes(
        self,
        conversation_id: str,
        runtime_url: Optional[str] = None,  # noqa: ARG002 - kept for V0 API compat
    ) -> Optional[List[Dict[str, str]]]:
        """
        Get git changes (uncommitted files) from the conversation workspace.

        Uses the Agent Server API to retrieve git changes. Requires a running sandbox.

        Args:
            conversation_id: Unique conversation identifier
            runtime_url: Deprecated - V1 retrieves this from sandbox info automatically

        Returns:
            List of file change dictionaries, or None if not a git repository

        Raises:
            SandboxNotRunningError: If sandbox is not running
            requests.HTTPError: If the API request fails
        """
        agent_server_url, session_api_key, _ = self._get_agent_server_info(
            conversation_id
        )

        # Agent Server endpoint for git changes - use '.' for workspace root
        response = self._make_agent_server_request(
            agent_server_url=agent_server_url,
            session_api_key=session_api_key,
            method="GET",
            endpoint="/api/git/changes/.",
        )

        if response.status_code == 404:
            # Not a git repository or no changes
            return None
        if response.status_code == 500:
            # Server error - likely git repository issue
            raise Exception("Git repository not available or corrupted")

        response.raise_for_status()
        return cast("Optional[List[Dict[str, str]]]", response.json())

    def get_file_content(
        self,
        conversation_id: str,
        file_path: str,
        runtime_url: Optional[str] = None,  # noqa: ARG002 - kept for V0 API compat
    ) -> Optional[str]:
        """
        Get file content from conversation workspace.

        Uses the Agent Server API to download file content. Requires a running sandbox.

        Args:
            conversation_id: Unique conversation identifier
            file_path: Path to file in workspace (e.g., 'README.md' or 'src/main.py')
            runtime_url: Deprecated - V1 retrieves this from sandbox info automatically

        Returns:
            File content as string or None if not found

        Raises:
            SandboxNotRunningError: If sandbox is not running
            requests.HTTPError: If the API request fails
        """
        agent_server_url, session_api_key, _ = self._get_agent_server_info(
            conversation_id
        )

        # Agent Server endpoint: GET /api/file/download/{path}
        # Path should be relative to workspace
        clean_path = file_path.lstrip("/")
        endpoint = f"/api/file/download/{clean_path}"

        response = self._make_agent_server_request(
            agent_server_url=agent_server_url,
            session_api_key=session_api_key,
            method="GET",
            endpoint=endpoint,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.text

    def download_workspace_archive(
        self,
        conversation_id: str,
        runtime_url: Optional[str] = None,  # noqa: ARG002 - kept for V0 API compat
        workspace_path: str = "/workspace",
    ) -> Optional[bytes]:
        """
        Download workspace archive as a ZIP file.

        Uses the Agent Server's bash endpoint to create a zip archive of the
        workspace, then downloads the resulting file. Requires a running sandbox.

        Args:
            conversation_id: Unique conversation identifier
            runtime_url: Deprecated - V1 retrieves this from sandbox info automatically
            workspace_path: Path to the workspace directory (default: /workspace)

        Returns:
            ZIP archive content as bytes, or None if workspace doesn't exist

        Raises:
            SandboxNotRunningError: If sandbox is not running
            requests.HTTPError: If the API request fails
            Exception: If zip creation fails
        """
        agent_server_url, session_api_key, _ = self._get_agent_server_info(
            conversation_id
        )

        # Create a unique temp file path for the zip
        temp_zip_path = f"/tmp/workspace-{uuid.uuid4().hex}.zip"

        # Use bash endpoint to create the zip archive
        zip_command = f"zip -r {temp_zip_path} {workspace_path}"
        bash_response = self._make_agent_server_request(
            agent_server_url=agent_server_url,
            session_api_key=session_api_key,
            method="POST",
            endpoint="/api/bash/execute_bash_command",
            json_data={"command": zip_command, "timeout": 120},
            timeout=130,  # Allow extra time for large workspaces
        )

        if bash_response.status_code != 200:
            bash_response.raise_for_status()

        result = bash_response.json()
        exit_code = result.get("exit_code", -1)
        if exit_code != 0:
            stderr = result.get("stderr", "Unknown error")
            raise Exception(f"Failed to create workspace archive: {stderr}")

        # Download the zip file
        download_response = self._make_agent_server_request(
            agent_server_url=agent_server_url,
            session_api_key=session_api_key,
            method="GET",
            endpoint=f"/api/file/download/{temp_zip_path}",
            timeout=120,  # Allow time for large downloads
        )

        if download_response.status_code == 404:
            return None

        download_response.raise_for_status()
        zip_content = download_response.content

        # Clean up the temp file (best effort)
        with contextlib.suppress(Exception):
            self._make_agent_server_request(
                agent_server_url=agent_server_url,
                session_api_key=session_api_key,
                method="POST",
                endpoint="/api/bash/execute_bash_command",
                json_data={"command": f"rm -f {temp_zip_path}", "timeout": 10},
                timeout=15,
            )

        return zip_content

    def get_trajectory(
        self,
        conversation_id: str,
        runtime_url: Optional[str] = None,  # noqa: ARG002 - kept for V0 API compat
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation trajectory from the Agent Server.

        Uses the Agent Server API to download the trajectory file.
        Requires a running sandbox.

        Args:
            conversation_id: Unique conversation identifier
            runtime_url: Deprecated - V1 retrieves this from sandbox info automatically

        Returns:
            List of trajectory events or None if not found

        Raises:
            SandboxNotRunningError: If sandbox is not running
            requests.HTTPError: If the API request fails
        """
        agent_server_url, session_api_key, _ = self._get_agent_server_info(
            conversation_id
        )

        # Agent Server endpoint: GET /api/file/download-trajectory/{conversation_id}
        endpoint = f"/api/file/download-trajectory/{conversation_id}"

        response = self._make_agent_server_request(
            agent_server_url=agent_server_url,
            session_api_key=session_api_key,
            method="GET",
            endpoint=endpoint,
            timeout=60,  # Trajectory can be large, allow more time
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return cast("Optional[List[Dict[str, Any]]]", response.json())
