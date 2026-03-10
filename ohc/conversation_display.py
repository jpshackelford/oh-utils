"""
Shared conversation display functionality for both CLI and interactive modes.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .api import OpenHandsAPI


@dataclass
class Conversation:
    """Represents a conversation with all relevant information"""

    id: str
    title: str
    status: str
    runtime_status: Optional[str]
    runtime_id: Optional[str]
    session_api_key: Optional[str]
    last_updated: str
    created_at: str
    url: Optional[str]
    version: Optional[str] = None

    @classmethod
    def from_api_response(
        cls, data: Dict[str, Any], api_base_url: Optional[str] = None
    ) -> "Conversation":
        """Create Conversation from API response data.

        Handles both V0 and V1 API response formats.

        Args:
            data: API response data for a conversation
            api_base_url: Optional base URL of the API server, used to resolve
                          relative URLs returned by some enterprise servers
        """
        # Handle both v0 and v1 API response formats for URL
        # v1 API uses conversation_url instead of url
        # Note: We explicitly check for None to preserve empty strings if present
        url = data.get("url")
        if url is None:
            url = data.get("conversation_url")

        # If URL is relative and we have a base URL, make it absolute
        if url and api_base_url and url.startswith("/"):
            from urllib.parse import urljoin

            # Remove trailing /api/ from base URL to get the server root
            base = api_base_url.rstrip("/")
            if base.endswith("/api"):
                base = base[:-4]
            url = urljoin(base, url)

        # Extract runtime ID from multiple sources for maximum compatibility
        # Priority: 1) Direct runtime_id field, 2) URL hostname, 3) sandbox_id,
        #           4) conversation_id (fallback for enterprise servers)
        runtime_id = data.get("runtime_id")  # Some servers may provide this directly

        # Try to extract from URL if not directly provided
        if not runtime_id and url:
            try:
                # Try to extract runtime ID from URL for display purposes
                # This is more flexible and doesn't assume specific domain patterns
                from urllib.parse import urlparse

                parsed_url = urlparse(url)
                if parsed_url.hostname:
                    # Extract the first part of the hostname as runtime ID
                    runtime_id = parsed_url.hostname.split(".")[0]
            except (IndexError, AttributeError, ValueError):
                pass

        # V1 fallback: use sandbox_id if available and no runtime_id yet
        if not runtime_id:
            runtime_id = data.get("sandbox_id")

        # Handle both v0 and v1 API response formats
        conversation_id = data.get("conversation_id") or data.get("id", "")

        # Handle status - v1 API uses different status fields
        status = data.get("status")
        if not status:
            # v1 API uses sandbox_status and execution_status
            sandbox_status = data.get("sandbox_status", "UNKNOWN")
            # Map v1 statuses to v0-like format
            if sandbox_status == "RUNNING":
                status = "RUNNING"
            elif sandbox_status == "PAUSED":
                status = "PAUSED"
            elif sandbox_status in ["STOPPED", "FINISHED"]:
                status = "STOPPED"
            else:
                status = sandbox_status

        # Extract version information if available
        version = data.get("conversation_version")

        return cls(
            id=conversation_id,
            title=data.get("title", "Untitled"),
            status=status,
            runtime_status=data.get("runtime_status"),
            runtime_id=runtime_id,
            session_api_key=data.get("session_api_key"),
            last_updated=data.get("last_updated_at") or data.get("updated_at", ""),
            created_at=data.get("created_at", ""),
            url=url,
            version=version,
        )

    def is_active(self) -> bool:
        """Check if conversation is currently active/running"""
        return self.status == "RUNNING" and self.runtime_id is not None

    def short_id(self) -> str:
        """Get shortened conversation ID for display"""
        return self.id[:8] if self.id else "unknown"

    def formatted_title(self, max_length: int = 50) -> str:
        """Get formatted title with length limit"""
        if len(self.title) <= max_length:
            return self.title
        return self.title[: max_length - 3] + "..."

    def status_display(self) -> str:
        """Get formatted status for display"""
        if self.is_active():
            return f"🟢 {self.status}"
        elif self.status == "STOPPED":
            return f"🔴 {self.status}"
        else:
            return f"🟡 {self.status}"

    def get_runtime_base_url(self) -> Optional[str]:
        """Extract the runtime base URL from the conversation URL.

        Returns the scheme://host portion of the URL, or None if no URL is set.
        This is useful for making API calls to the runtime server.
        """
        if not self.url:
            return None
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except (AttributeError, ValueError):
            return None


def show_conversation_details(api: OpenHandsAPI, conversation_id: str) -> None:
    """Show detailed information about a conversation"""
    try:
        # Get fresh data from API
        data = api.get_conversation(conversation_id)
        if data is None:
            print(f"Error: Conversation {conversation_id} not found")
            return
        conv = Conversation.from_api_response(data, api.base_url)

        print("\nConversation Details:")
        print(f"  ID: {conv.id}")
        print(f"  Title: {conv.title}")
        print(f"  Status: {conv.status_display()}")
        print(f"  Runtime Status: {conv.runtime_status or 'N/A'}")
        print(f"  Runtime ID: {conv.runtime_id or 'N/A'}")
        print(f"  Created: {conv.created_at}")
        print(f"  Last Updated: {conv.last_updated}")
        if conv.url:
            print(f"  URL: {conv.url}")

        # Show uncommitted files for running conversations
        if conv.is_active():
            try:
                runtime_url = conv.get_runtime_base_url()
                changes = api.get_conversation_changes(
                    conv.id, runtime_url, conv.session_api_key
                )
                if changes:
                    print(f"\n  Uncommitted Files ({len(changes)}):")

                    # Group changes by status
                    status_groups: Dict[str, List[str]] = {}
                    for change in changes:
                        status = change["status"]
                        if status not in status_groups:
                            status_groups[status] = []
                        status_groups[status].append(change["path"])

                    # Display changes by status with icons
                    status_icons = {
                        "M": "📝",  # Modified
                        "A": "➕",  # Added/New
                        "D": "🗑️",  # Deleted
                        "U": "⚠️",  # Unmerged/Conflict
                    }

                    status_names = {
                        "M": "Modified",
                        "A": "Added/New",
                        "D": "Deleted",
                        "U": "Unmerged",
                    }

                    for status in ["M", "A", "D", "U"]:
                        if status in status_groups:
                            icon = status_icons.get(status, "•")
                            name = status_names.get(status, status)
                            files = status_groups[status]
                            print(f"    {icon} {name} ({len(files)}):")
                            for file_path in sorted(files):
                                print(f"      {file_path}")
                else:
                    print("\n  No changes identified")
            except Exception as e:
                error_msg = str(e)
                if "Git repository not available or corrupted" in error_msg:
                    print("\n  ⚠️  Git repository not available for this conversation")
                    print(
                        "      This may happen if the conversation workspace "
                        "doesn't have git initialized"
                    )
                elif "HTTP 401" in error_msg or "Unauthorized" in error_msg:
                    print(
                        "\n  ⚠️  API key doesn't have permission to access git changes"
                    )
                else:
                    print(f"\n  ⚠️  Could not fetch uncommitted files: {error_msg}")

        print()
    except Exception as e:
        print(f"✗ Failed to get conversation details: {e}")


def show_workspace_changes(api: OpenHandsAPI, conversation_id: str) -> None:
    """Show workspace file changes (git status) for a conversation"""
    try:
        # Get conversation details first
        data = api.get_conversation(conversation_id)
        if data is None:
            print(f"Error: Conversation {conversation_id} not found")
            return
        conv = Conversation.from_api_response(data, api.base_url)

        if not conv.is_active():
            print(f"⚠️  Conversation {conv.short_id()} is not currently running")
            print("   Workspace changes are only available for active conversations")
            return

        try:
            runtime_url = conv.get_runtime_base_url()
            changes = api.get_conversation_changes(
                conv.id, runtime_url, conv.session_api_key
            )
            if changes:
                print(f"\nWorkspace Changes for {conv.short_id()}:")
                print(f"Title: {conv.title}")
                print(f"Total files changed: {len(changes)}")

                # Group changes by status
                status_groups: Dict[str, List[str]] = {}
                for change in changes:
                    status = change["status"]
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(change["path"])

                # Display changes by status with icons
                status_icons = {
                    "M": "📝",  # Modified
                    "A": "➕",  # Added/New
                    "D": "🗑️",  # Deleted
                    "U": "⚠️",  # Unmerged/Conflict
                }

                status_names = {
                    "M": "Modified",
                    "A": "Added/New",
                    "D": "Deleted",
                    "U": "Unmerged",
                }

                for status in ["M", "A", "D", "U"]:
                    if status in status_groups:
                        icon = status_icons.get(status, "•")
                        name = status_names.get(status, status)
                        files = status_groups[status]
                        print(f"\n{icon} {name} ({len(files)}):")
                        for file_path in sorted(files):
                            print(f"  {file_path}")
            else:
                print(f"\nNo changes found for conversation {conv.short_id()}")
                print(f"Title: {conv.title}")
                print("The workspace appears to be clean (no uncommitted changes)")
        except Exception as e:
            error_msg = str(e)
            if "Git repository not available or corrupted" in error_msg:
                print(
                    f"\n⚠️  Git repository not available for conversation "
                    f"{conv.short_id()}"
                )
                print(
                    "   This may happen if the conversation workspace doesn't have "
                    "git initialized"
                )
            elif "HTTP 401" in error_msg or "Unauthorized" in error_msg:
                print("\n⚠️  API key doesn't have permission to access git changes")
            else:
                print(f"\n⚠️  Could not fetch workspace changes: {error_msg}")

    except Exception as e:
        print(f"✗ Failed to get conversation information: {e}")
