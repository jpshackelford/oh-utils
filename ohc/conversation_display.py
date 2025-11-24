"""
Shared conversation display functionality for both CLI and interactive modes.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

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

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create Conversation from API response data"""
        # Extract runtime ID from URL if available
        runtime_id = None
        if data.get('url'):
            try:
                # URL format: https://{runtime_id}.prod-runtime.all-hands.dev/...
                runtime_id = data['url'].split('.')[0].split('//')[1]
            except (IndexError, AttributeError):
                runtime_id = None

        return cls(
            id=data['conversation_id'],
            title=data.get('title', 'Untitled'),
            status=data.get('status', 'UNKNOWN'),
            runtime_status=data.get('runtime_status'),
            runtime_id=runtime_id,
            session_api_key=data.get('session_api_key'),
            last_updated=data.get('last_updated_at', ''),
            created_at=data.get('created_at', ''),
            url=data.get('url')
        )

    def is_active(self) -> bool:
        """Check if conversation is currently active/running"""
        return self.status == 'RUNNING' and self.runtime_id is not None

    def short_id(self) -> str:
        """Get shortened conversation ID for display"""
        return self.id[:8] if self.id else 'unknown'

    def formatted_title(self, max_length: int = 50) -> str:
        """Get formatted title with length limit"""
        if len(self.title) <= max_length:
            return self.title
        return self.title[:max_length-3] + "..."

    def status_display(self) -> str:
        """Get formatted status for display"""
        if self.is_active():
            return f"🟢 {self.status}"
        elif self.status == 'STOPPED':
            return f"🔴 {self.status}"
        else:
            return f"🟡 {self.status}"


def show_conversation_details(api: OpenHandsAPI, conversation_id: str) -> None:
    """Show detailed information about a conversation"""
    try:
        # Get fresh data from API
        data = api.get_conversation(conversation_id)
        conv = Conversation.from_api_response(data)

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
                changes = api.get_conversation_changes(conv.id, conv.runtime_id, conv.session_api_key)
                if changes:
                    print(f"\n  Uncommitted Files ({len(changes)}):")

                    # Group changes by status
                    status_groups = {}
                    for change in changes:
                        status = change['status']
                        if status not in status_groups:
                            status_groups[status] = []
                        status_groups[status].append(change['path'])

                    # Display changes by status with icons
                    status_icons = {
                        'M': '📝',  # Modified
                        'A': '➕',  # Added/New
                        'D': '🗑️',  # Deleted
                        'U': '⚠️'   # Unmerged/Conflict
                    }

                    status_names = {
                        'M': 'Modified',
                        'A': 'Added/New',
                        'D': 'Deleted',
                        'U': 'Unmerged'
                    }

                    for status in ['M', 'A', 'D', 'U']:
                        if status in status_groups:
                            icon = status_icons.get(status, '•')
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
                    print("      This may happen if the conversation workspace doesn't have git initialized")
                elif "HTTP 401" in error_msg or "Unauthorized" in error_msg:
                    print("\n  ⚠️  API key doesn't have permission to access git changes")
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
        conv = Conversation.from_api_response(data)

        if not conv.is_active():
            print(f"⚠️  Conversation {conv.short_id()} is not currently running")
            print("   Workspace changes are only available for active conversations")
            return

        try:
            changes = api.get_conversation_changes(conv.id, conv.runtime_id, conv.session_api_key)
            if changes:
                print(f"\nWorkspace Changes for {conv.short_id()}:")
                print(f"Title: {conv.title}")
                print(f"Total files changed: {len(changes)}")

                # Group changes by status
                status_groups = {}
                for change in changes:
                    status = change['status']
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(change['path'])

                # Display changes by status with icons
                status_icons = {
                    'M': '📝',  # Modified
                    'A': '➕',  # Added/New
                    'D': '🗑️',  # Deleted
                    'U': '⚠️'   # Unmerged/Conflict
                }

                status_names = {
                    'M': 'Modified',
                    'A': 'Added/New',
                    'D': 'Deleted',
                    'U': 'Unmerged'
                }

                for status in ['M', 'A', 'D', 'U']:
                    if status in status_groups:
                        icon = status_icons.get(status, '•')
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
                print(f"\n⚠️  Git repository not available for conversation {conv.short_id()}")
                print("   This may happen if the conversation workspace doesn't have git initialized")
            elif "HTTP 401" in error_msg or "Unauthorized" in error_msg:
                print("\n⚠️  API key doesn't have permission to access git changes")
            else:
                print(f"\n⚠️  Could not fetch workspace changes: {error_msg}")

    except Exception as e:
        print(f"✗ Failed to get conversation information: {e}")
