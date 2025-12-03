"""
OpenHands v1 API client for the ohc CLI.

This module implements the v1 API endpoints which use /v1 prefixes
and provide enhanced functionality for events and app-conversations.
"""

from typing import Any, Dict, List, Optional, cast
from urllib.parse import urljoin

import requests


class OpenHandsAPI:
    """
    OpenHands v1 API client for conversation and event management.

    This client provides access to the v1 API endpoints which include
    enhanced event search, app-conversation management, and improved
    data structures.

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
        self.session.headers.update(
            {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
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
        Get conversation details (compatibility method).

        Note: This method may need to be implemented based on actual v1 API
        endpoints when they become available.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation dictionary or None if not found

        Raises:
            requests.HTTPError: If the API request fails
        """
        # For now, this is a placeholder - actual v1 implementation
        # would depend on available endpoints
        raise NotImplementedError(
            "get_conversation not yet implemented for v1 API. "
            "Use search_app_conversations to find conversations."
        )

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
                "conversation_status": data.get("status", "WORKING")
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create conversation - {str(e)}") from e

    def start_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new conversation (compatibility method).

        Note: This method may need to be implemented based on actual v1 API
        endpoints when they become available.

        Args:
            conversation_data: Conversation configuration

        Returns:
            Started conversation dictionary

        Raises:
            requests.HTTPError: If the API request fails
        """
        # For now, this is a placeholder - actual v1 implementation
        # would depend on available endpoints
        raise NotImplementedError("start_conversation not yet implemented for v1 API")

    def get_conversation_changes(
        self, conversation_id: str, runtime_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation workspace changes (compatibility method).

        Args:
            conversation_id: Unique conversation identifier
            runtime_url: Optional runtime URL for the conversation

        Returns:
            Changes dictionary or None if not found

        Raises:
            requests.HTTPError: If the API request fails
        """
        # For now, this is a placeholder - actual v1 implementation
        # would depend on available endpoints
        raise NotImplementedError(
            "get_conversation_changes not yet implemented for v1 API"
        )

    def get_file_content(
        self, conversation_id: str, file_path: str, runtime_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Get file content from conversation workspace (compatibility method).

        Args:
            conversation_id: Unique conversation identifier
            file_path: Path to the file in the workspace
            runtime_url: Optional runtime URL for the conversation

        Returns:
            File content as string or None if not found

        Raises:
            requests.HTTPError: If the API request fails
        """
        # For now, this is a placeholder - actual v1 implementation
        # would depend on available endpoints
        raise NotImplementedError("get_file_content not yet implemented for v1 API")

    def download_workspace_archive(
        self, conversation_id: str, runtime_url: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Download workspace archive (compatibility method).

        Args:
            conversation_id: Unique conversation identifier
            runtime_url: Optional runtime URL for the conversation

        Returns:
            Archive content as bytes or None if not found

        Raises:
            requests.HTTPError: If the API request fails
        """
        # For now, this is a placeholder - actual v1 implementation
        # would depend on available endpoints
        raise NotImplementedError(
            "download_workspace_archive not yet implemented for v1 API"
        )

    def get_trajectory(
        self, conversation_id: str, runtime_url: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation trajectory (compatibility method).

        Args:
            conversation_id: Unique conversation identifier
            runtime_url: Optional runtime URL for the conversation

        Returns:
            List of trajectory events or None if not found

        Raises:
            requests.HTTPError: If the API request fails
        """
        # For now, this is a placeholder - actual v1 implementation
        # would depend on available endpoints
        raise NotImplementedError("get_trajectory not yet implemented for v1 API")
