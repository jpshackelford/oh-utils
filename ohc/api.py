"""
OpenHands API client with version selection support.

This module provides a unified interface for accessing both v0 and v1
OpenHands APIs, with automatic version selection based on configuration
or explicit version parameters.
"""

from typing import Any, Dict, List, Optional, Union, cast

from .v0.api import OpenHandsAPI as V0API
from .v1.api import OpenHandsAPI as V1API


class OpenHandsAPI:
    """
    Unified OpenHands API client with version selection.

    This wrapper class provides access to both v0 and v1 APIs,
    automatically selecting the appropriate version based on
    configuration or explicit parameters.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://app.all-hands.dev/api/",
        version: str = "v0",
    ):
        """
        Initialize the OpenHands API client with version selection.

        Args:
            api_key: OpenHands API key from https://app.all-hands.dev/settings/api-keys
            base_url: Base URL for the API endpoint, defaults to production
            version: API version to use ("v0" or "v1"), defaults to "v0"
        """
        self.api_key = api_key
        self.base_url = base_url
        self.version = version

        self._client: Union[V0API, V1API]
        if version == "v0":
            self._client = V0API(api_key, base_url)
        elif version == "v1":
            self._client = V1API(api_key, base_url)
        else:
            raise ValueError(f"Unsupported API version: {version}. Use 'v0' or 'v1'.")

    @property
    def client(self) -> Union[V0API, V1API]:
        """Get the underlying API client."""
        return self._client

    def test_connection(self) -> bool:
        """Test if the API key and URL are valid."""
        return self._client.test_connection()

    def search_conversations(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search conversations using the selected API version.

        Returns a normalized response structure regardless of API version:
        - Results wrapped in {"results": [...]}
        - Each conversation has "conversation_id" field (normalized from V1's "id")
        """
        if self.version == "v0":
            # v0 API uses page_id and limit, returns a dict with results
            # For now, ignore query and offset since v0 doesn't support them
            return cast("V0API", self._client).search_conversations(limit=limit)
        else:
            # v1 API supports query, limit, and offset directly
            results = cast("V1API", self._client).search_conversations(
                query=query, limit=limit, offset=offset
            )
            # Normalize V1 response: map "id" to "conversation_id" for compatibility
            normalized_results = []
            for conv in results:
                if isinstance(conv, dict):
                    normalized_conv = dict(conv)
                    if "id" in normalized_conv and "conversation_id" not in normalized_conv:
                        normalized_conv["conversation_id"] = normalized_conv["id"]
                    normalized_results.append(normalized_conv)
                else:
                    normalized_results.append(conv)
            return {"results": normalized_results}

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation details using the selected API version."""
        return self._client.get_conversation(conversation_id)

    def create_conversation(self) -> Dict[str, Any]:
        """Create a new conversation using the selected API version."""
        return self._client.create_conversation()

    def start_conversation(
        self,
        conversation_id: str,
        providers_set: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Start/wake up a conversation using the selected API version.

        Args:
            conversation_id: The conversation ID to start
            providers_set: Optional list of providers (V0 only)

        Returns:
            Dictionary containing conversation start response
        """
        if self.version == "v0":
            return cast("V0API", self._client).start_conversation(
                conversation_id, providers_set
            )
        else:
            return cast("V1API", self._client).start_conversation(
                conversation_id, providers_set
            )

    def get_conversation_changes(
        self,
        conversation_id: str,
        runtime_url: Optional[str] = None,
        session_api_key: Optional[str] = None,
    ) -> Optional[List[Dict[str, str]]]:
        """Get conversation workspace changes using the selected API version."""
        if self.version == "v0":
            # v0 API has an extra session_api_key parameter
            return cast("V0API", self._client).get_conversation_changes(
                conversation_id, runtime_url, session_api_key
            )
        else:
            # v1 API returns Optional[List[Dict[str, str]]] directly
            return cast("V1API", self._client).get_conversation_changes(
                conversation_id, runtime_url
            )

    def get_file_content(
        self,
        conversation_id: str,
        file_path: str,
        runtime_url: Optional[str] = None,
        session_api_key: Optional[str] = None,
    ) -> Optional[str]:
        """Get file content from conversation workspace."""
        if self.version == "v0":
            # v0 API has an extra session_api_key parameter
            return cast("V0API", self._client).get_file_content(
                conversation_id, file_path, runtime_url, session_api_key
            )
        else:
            return cast("V1API", self._client).get_file_content(
                conversation_id, file_path, runtime_url
            )

    def download_workspace_archive(
        self,
        conversation_id: str,
        runtime_url: Optional[str] = None,
        session_api_key: Optional[str] = None,
    ) -> Optional[bytes]:
        """Download workspace archive using the selected API version."""
        if self.version == "v0":
            # v0 API has an extra session_api_key parameter
            return cast("V0API", self._client).download_workspace_archive(
                conversation_id, runtime_url, session_api_key
            )
        else:
            return cast("V1API", self._client).download_workspace_archive(
                conversation_id, runtime_url
            )

    def get_trajectory(
        self,
        conversation_id: str,
        runtime_url: Optional[str] = None,
        session_api_key: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get conversation trajectory using the selected API version."""
        if self.version == "v0":
            # v0 API requires runtime_url and session_api_key as required parameters
            if not runtime_url:
                return None
            result = cast("V0API", self._client).get_trajectory(
                conversation_id, runtime_url, session_api_key or self.api_key
            )
            # v0 returns Dict[str, Any], convert to List format for consistency
            if isinstance(result, dict) and "trajectory" in result:
                return cast("List[Dict[str, Any]]", result["trajectory"])
            return None
        else:
            return cast("V1API", self._client).get_trajectory(
                conversation_id, runtime_url
            )

    # V1-specific methods (only available when using v1)

    def search_events(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        event_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search events using the v1 API.

        Raises:
            AttributeError: If called with v0 API
        """
        if self.version != "v1":
            raise AttributeError("search_events is only available in v1 API")
        return cast("V1API", self._client).search_events(
            query=query,
            limit=limit,
            offset=offset,
            event_type=event_type,
            conversation_id=conversation_id,
        )

    def get_events_count(
        self,
        query: Optional[str] = None,
        event_type: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> int:
        """
        Get count of events matching criteria using the v1 API.

        Raises:
            AttributeError: If called with v0 API
        """
        if self.version != "v1":
            raise AttributeError("get_events_count is only available in v1 API")
        return cast("V1API", self._client).get_events_count(
            query=query, event_type=event_type, conversation_id=conversation_id
        )

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new event using the v1 API.

        Raises:
            AttributeError: If called with v0 API
        """
        if self.version != "v1":
            raise AttributeError("create_event is only available in v1 API")
        return cast("V1API", self._client).create_event(event_data)

    def search_app_conversations(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search app conversations using the v1 API.

        Raises:
            AttributeError: If called with v0 API
        """
        if self.version != "v1":
            raise AttributeError("search_app_conversations is only available in v1 API")
        return cast("V1API", self._client).search_app_conversations(
            query=query, limit=limit, offset=offset, status=status
        )

    def get_app_conversations_count(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        Get count of app conversations matching criteria using the v1 API.

        Raises:
            AttributeError: If called with v0 API
        """
        if self.version != "v1":
            raise AttributeError(
                "get_app_conversations_count is only available in v1 API"
            )
        return cast("V1API", self._client).get_app_conversations_count(
            query=query, status=status
        )


def create_api_client(
    api_key: str, base_url: str = "https://app.all-hands.dev/api/", version: str = "v0"
) -> OpenHandsAPI:
    """
    Factory function to create an OpenHands API client.

    Args:
        api_key: OpenHands API key
        base_url: Base URL for the API endpoint
        version: API version to use ("v0" or "v1")

    Returns:
        Configured OpenHands API client
    """
    return OpenHandsAPI(api_key, base_url, version)
