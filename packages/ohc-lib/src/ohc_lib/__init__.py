"""
OpenHands Cloud API Client Library (ohc-lib)

A Python library for programmatic access to OpenHands Cloud and Agent Server REST APIs.
Designed for administrators and developers who need to automate OpenHands operations.

Example usage:
    from ohc_lib import OpenHandsAPI

    # Create a client for the v1 API
    api = OpenHandsAPI(api_key="your-api-key", version="v1")

    # List conversations
    result = api.search_conversations(limit=10)
    for conv in result["results"]:
        print(f"{conv['conversation_id']}: {conv.get('title', 'Untitled')}")

    # Get conversation details
    details = api.get_conversation("conversation-id")

For v0 or v1 specific clients:
    from ohc_lib.v0 import OpenHandsAPI as V0API
    from ohc_lib.v1 import OpenHandsAPI as V1API
"""

__version__ = "0.1.0"

from .api import OpenHandsAPI, create_api_client
from .v1.api import SandboxNotRunningError

__all__ = [
    "OpenHandsAPI",
    "create_api_client",
    "SandboxNotRunningError",
    "__version__",
]
