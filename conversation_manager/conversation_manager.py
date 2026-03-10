#!/usr/bin/env python3
"""
OpenHands Conversation Manager

A terminal-based utility to list, manage, and interact with OpenHands conversations.
Features:
- List conversations with status and runtime IDs
- Terminal-aware formatting with pagination
- Wake up specific conversations
- Refresh conversation list
- Interactive command interface
"""

import json
import os
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

# Import consolidated API client with version support
from ohc.api import OpenHandsAPI

# Import shared display functionality
try:
    from ohc.conversation_display import (
        show_conversation_details as shared_show_conversation_details,
    )
except ImportError:
    # Fallback if ohc module is not available
    def shared_show_conversation_details(*args: Any, **kwargs: Any) -> None:
        pass


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
    def from_api_response(cls, data: Dict[str, Any]) -> "Conversation":
        """Create Conversation from API response data.

        Handles both V0 and V1 API response formats.
        """
        # Extract runtime ID from URL if available (for backward compatibility)
        # Note: This is kept for display purposes only, the URL should be used
        # directly for API calls
        runtime_id = None
        url = data.get("url") or data.get("conversation_url")
        if url:
            try:
                # Try to extract runtime ID from URL for display purposes
                # This is more flexible and doesn't assume specific domain patterns
                from urllib.parse import urlparse

                parsed_url = urlparse(url)
                if parsed_url.hostname:
                    # Extract the first part of the hostname as runtime ID
                    runtime_id = parsed_url.hostname.split(".")[0]
            except (IndexError, AttributeError, ValueError):
                runtime_id = None

        # Handle both v0 and v1 API response formats
        conversation_id = data.get("conversation_id") or data.get("id", "")

        # Handle status - v1 API uses different status fields
        status = data.get("status")
        if not status:
            # v1 API uses sandbox_status and execution_status
            sandbox_status = data.get("sandbox_status", "UNKNOWN")
            if sandbox_status == "RUNNING":
                status = "RUNNING"
            elif sandbox_status == "PAUSED":
                status = "PAUSED"
            elif sandbox_status == "STOPPED":
                status = "STOPPED"
            else:
                status = sandbox_status

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


class APIKeyManager:
    """Manages OpenHands API key storage and retrieval"""

    DEFAULT_BASE_URL = "https://app.all-hands.dev/api/"

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.config_dir = Path.home() / ".openhands"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        self.base_url = base_url or self.DEFAULT_BASE_URL

    def get_stored_key(self) -> Optional[str]:
        """Get stored API key if it exists"""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    return cast("Optional[str]", config.get("api_key"))
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def store_key(self, api_key: str) -> None:
        """Store API key securely"""
        config = {"api_key": api_key}
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
        # Set restrictive permissions
        os.chmod(self.config_file, 0o600)

    def get_valid_key(self) -> str:
        """Get a valid API key, prompting user if necessary"""
        # Check environment variables first
        env_key = os.getenv("OH_API_KEY") or os.getenv("OPENHANDS_API_KEY")
        if env_key:
            api = OpenHandsAPI(env_key, self.base_url)
            if api.test_connection():
                try:
                    api.search_conversations(limit=1)
                    env_var = (
                        "OH_API_KEY" if os.getenv("OH_API_KEY") else "OPENHANDS_API_KEY"
                    )
                    print(f"✓ Using API key from {env_var} environment variable")
                    return env_key
                except Exception as e:
                    print(f"⚠️  Environment API key error: {e}")

        # Check stored key
        stored_key = self.get_stored_key()
        if stored_key:
            api = OpenHandsAPI(stored_key, self.base_url)
            if api.test_connection():
                try:
                    api.search_conversations(limit=1)
                    print("✓ Using stored API key")
                    return stored_key
                except Exception as e:
                    print(f"⚠️  Stored API key error: {e}")

        # Prompt for new key
        print("\nPlease get your OpenHands API key from:")
        # Show appropriate URL based on base_url
        if "app.all-hands.dev" in self.base_url:
            print("https://app.all-hands.dev/settings/api-keys")
        else:
            # Extract host from base_url for enterprise instances
            from urllib.parse import urlparse

            parsed = urlparse(self.base_url)
            print(f"https://{parsed.netloc}/settings/api-keys")
        print()

        while True:
            try:
                api_key = input("Enter your OpenHands API key: ").strip()
                if not api_key:
                    print("API key cannot be empty")
                    continue

                api = OpenHandsAPI(api_key, self.base_url)
                if api.test_connection():
                    try:
                        api.search_conversations(limit=1)
                        self.store_key(api_key)
                        print("✓ API key validated and stored")
                        return api_key
                    except Exception as e:
                        print(f"✗ API key validation failed: {e}")
                else:
                    print("✗ Invalid API key")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(1)


class TerminalFormatter:
    """Handles terminal formatting and display"""

    def __init__(self) -> None:
        self.terminal_size = self.get_terminal_size()

    def get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal width and height"""
        try:
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except Exception:
            return 80, 24  # Default fallback

    def clear_screen(self) -> None:
        """Clear the terminal screen"""
        os.system("clear" if os.name == "posix" else "cls")

    def format_conversations_table(
        self, conversations: List[Conversation], start_index: int = 0
    ) -> List[str]:
        """Format conversations as a table with proper column alignment"""
        if not conversations:
            return ["No conversations found."]

        width, _ = self.terminal_size

        # Calculate column widths based on terminal size
        # Widths: num(5) + id(10) + status(12) + runtime(17) + title(remaining)
        # Allow for 3-digit numbers with 2 spaces before ID
        min_width = 5 + 10 + 12 + 17 + 20  # 64 chars minimum

        if width < min_width:
            # Fallback for very narrow terminals
            lines = []
            for i, conv in enumerate(conversations, start_index + 1):
                lines.append(f"{i:3d}. {conv.short_id()} - {conv.status}")
                lines.append(f"     {conv.formatted_title(width - 5)}")
                if conv.runtime_id:
                    lines.append(f"     Runtime: {conv.runtime_id}")
                lines.append("")
            return lines

        # Calculate dynamic column widths
        num_width = 5  # Allow for 3-digit numbers + 2 spaces
        id_width = 10
        status_width = 12
        runtime_width = 17  # Increased for better spacing
        title_width = max(
            20, width - num_width - id_width - status_width - runtime_width - 4
        )  # 4 for separators

        # Header
        header = (
            f"{'#':>{num_width - 2}}  "  # Right-align number with 2 spaces
            f"{'ID':<{id_width}} "
            f"{'Status':<{status_width}} "
            f"{'Runtime':<{runtime_width}} "
            f"{'Title':<{title_width}}"
        )

        separator = "─" * min(len(header), width - 1)

        lines = [header, separator]

        # Conversation rows
        for i, conv in enumerate(conversations, start_index + 1):
            runtime_display = conv.runtime_id or "─"

            row = (
                f"{i:>{num_width - 2}}  "  # Right-align number with 2 spaces
                f"{conv.short_id():<{id_width}} "
                f"{conv.status_display():<{status_width}} "
                f"{runtime_display:<{runtime_width}} "
                f"{conv.formatted_title(title_width):<{title_width}}"
            )

            lines.append(row)

        return lines

    def format_help(self) -> List[str]:
        """Format help text"""
        return [
            "",
            "Commands:",
            "  r, refresh    - Refresh conversation list",
            "  w <num>       - Wake up conversation by number",
            "  s <num>       - Show detailed info for conversation",
            "  f <num>       - Download changed files as zip",
            "  t <num>       - Download trajectory as JSON",
            "  a <num>       - Download entire workspace as zip",
            "  n, next       - Next page",
            "  p, prev       - Previous page",
            "  q, quit       - Quit",
            "  h, help       - Show this help",
            "",
            "Examples:",
            "  w 3           - Wake up conversation #3",
            "  s 1           - Show details for conversation #1",
            "  f 2           - Download changed files from conversation #2",
            "  t 2           - Download trajectory from conversation #2",
            "  a 2           - Download entire workspace from conversation #2",
            "",
        ]


class ConversationManager:
    """Main conversation manager application"""

    def __init__(
        self, api_version: str = "v0", base_url: str = "https://app.all-hands.dev/api/"
    ) -> None:
        self.base_url = base_url
        self.api_key_manager = APIKeyManager(base_url=base_url)
        self.formatter = TerminalFormatter()
        self.api: Optional[OpenHandsAPI] = None
        self.conversations: List[Conversation] = []
        self.current_page = 0
        self.page_size = 20
        self.next_page_id: Optional[str] = None
        self.page_ids: List[Optional[str]] = [None]  # Track page IDs for navigation
        self.api_version = api_version

    def initialize(self) -> None:
        """Initialize the application with API key"""
        try:
            api_key = self.api_key_manager.get_valid_key()
            self.api = OpenHandsAPI(api_key, self.base_url, self.api_version)
            version_str = f" (API {self.api_version})" if self.api_version else ""
            print(f"✓ Conversation Manager initialized successfully{version_str}")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Failed to initialize: {e}")
            sys.exit(1)

    def load_conversations(
        self, page_id: Optional[str] = None, offset: int = 0
    ) -> bool:
        """Load conversations from API.

        Args:
            page_id: Page ID for V0 API pagination
            offset: Offset for V1 API pagination
        """
        try:
            if self.api is None:
                print("✗ API not initialized")
                return False

            # Adjust page size based on terminal height
            _, height = self.formatter.terminal_size
            # Reserve space for header, separator, help, and command prompt
            available_lines = max(5, height - 10)
            self.page_size = min(20, available_lines)

            if self.api_version == "v0":
                response = self.api.search_conversations(
                    page_id=page_id, limit=self.page_size
                )
                self.next_page_id = response.get("next_page_id")
            else:
                # V1 uses offset-based pagination
                response = self.api.search_conversations(
                    limit=self.page_size, offset=offset
                )
                # V1 doesn't have next_page_id, check if there might be more
                results = response.get("results", [])
                self.next_page_id = "more" if len(results) >= self.page_size else None

            conversations_data = response.get("results", [])
            self.conversations = [
                Conversation.from_api_response(data) for data in conversations_data
            ]

            return True
        except Exception as e:
            print(f"✗ Failed to load conversations: {e}")
            return False

    def refresh_conversations(self) -> None:
        """Refresh current page of conversations"""
        if self.api_version == "v0":
            current_page_id = (
                self.page_ids[self.current_page]
                if self.current_page < len(self.page_ids)
                else None
            )
            if self.load_conversations(page_id=current_page_id):
                print("✓ Conversations refreshed")
            else:
                print("✗ Failed to refresh conversations")
        else:
            # V1: use offset-based pagination
            offset = self.current_page * self.page_size
            if self.load_conversations(offset=offset):
                print("✓ Conversations refreshed")
            else:
                print("✗ Failed to refresh conversations")

    def next_page(self) -> None:
        """Go to next page"""
        if self.next_page_id:
            if self.api_version == "v0":
                if self.current_page + 1 >= len(self.page_ids):
                    self.page_ids.append(self.next_page_id)

                self.current_page += 1
                page_id = self.page_ids[self.current_page]

                if self.load_conversations(page_id=page_id):
                    print(f"✓ Moved to page {self.current_page + 1}")
                else:
                    self.current_page -= 1  # Revert on failure
                    print("✗ Failed to load next page")
            else:
                # V1: use offset-based pagination
                self.current_page += 1
                offset = self.current_page * self.page_size
                if self.load_conversations(offset=offset):
                    print(f"✓ Moved to page {self.current_page + 1}")
                else:
                    self.current_page -= 1  # Revert on failure
                    print("✗ Failed to load next page")
        else:
            print("No more pages available")

    def prev_page(self) -> None:
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            if self.api_version == "v0":
                page_id = self.page_ids[self.current_page]
                if self.load_conversations(page_id=page_id):
                    print(f"✓ Moved to page {self.current_page + 1}")
                else:
                    self.current_page += 1  # Revert on failure
                    print("✗ Failed to load previous page")
            else:
                # V1: use offset-based pagination
                offset = self.current_page * self.page_size
                if self.load_conversations(offset=offset):
                    print(f"✓ Moved to page {self.current_page + 1}")
                else:
                    self.current_page += 1  # Revert on failure
                    print("✗ Failed to load previous page")
        else:
            print("Already on first page")

    def wake_conversation(self, conv_number: int) -> None:
        """Wake up a conversation by its display number"""
        if 1 <= conv_number <= len(self.conversations):
            conv = self.conversations[conv_number - 1]
            try:
                if self.api is None:
                    print("✗ API not initialized")
                    return

                print(f"Waking up conversation: {conv.formatted_title()}")
                self.api.start_conversation(conv.id)
                print("✓ Conversation started successfully")

                # Refresh to get updated status
                self.refresh_conversations()
            except Exception as e:
                error_msg = f"✗ Failed to wake conversation: {e}"
                print(error_msg)
                print(f"Conversation ID: {conv.id}")
                print(f"Conversation Title: {conv.formatted_title()}")
                input("Press Enter to continue...")
        else:
            print(f"Invalid conversation number: {conv_number}")
            input("Press Enter to continue...")

    def show_conversation_details(self, conv_number: int) -> None:
        """Show detailed information about a conversation"""
        if 1 <= conv_number <= len(self.conversations):
            conv = self.conversations[conv_number - 1]
            try:
                if self.api is None:
                    print("✗ API not initialized")
                    return

                # Get fresh data from API
                data = self.api.get_conversation(conv.id)
                if data is None:
                    print(f"✗ Conversation {conv.id} not found")
                    return
                fresh_conv = Conversation.from_api_response(data)

                print("\nConversation Details:")
                print(f"  ID: {fresh_conv.id}")
                print(f"  Title: {fresh_conv.title}")
                print(f"  Status: {fresh_conv.status_display()}")
                print(f"  Runtime Status: {fresh_conv.runtime_status or 'N/A'}")
                print(f"  Runtime ID: {fresh_conv.runtime_id or 'N/A'}")
                print(f"  Created: {fresh_conv.created_at}")
                print(f"  Last Updated: {fresh_conv.last_updated}")
                if fresh_conv.url:
                    print(f"  URL: {fresh_conv.url}")

                # Show uncommitted files for running conversations
                if fresh_conv.is_active():
                    try:
                        # Extract runtime base URL from conversation URL
                        runtime_url = None
                        if fresh_conv.url:
                            from urllib.parse import urlparse

                            parsed_url = urlparse(fresh_conv.url)
                            runtime_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                        changes = self.api.get_conversation_changes(
                            fresh_conv.id,
                            runtime_url,
                            fresh_conv.session_api_key,
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
                            print(
                                "\n  ⚠️  Git repository not available for this "
                                "conversation"
                            )
                            print(
                                "      This may happen if the conversation workspace "
                                "doesn't have git initialized"
                            )
                        elif "HTTP 401" in error_msg or "Unauthorized" in error_msg:
                            print(
                                "\n  ⚠️  API key doesn't have permission to access "
                                "git changes"
                            )
                        else:
                            print(
                                f"\n  ⚠️  Could not fetch uncommitted files: {error_msg}"
                            )

                print()
            except Exception as e:
                print(f"✗ Failed to get conversation details: {e}")
        else:
            print(f"Invalid conversation number: {conv_number}")

    def download_conversation_files(self, conv_number: int) -> None:
        """Download all changed files from a conversation as a zip file"""
        if not (1 <= conv_number <= len(self.conversations)):
            print(f"Invalid conversation number: {conv_number}")
            return

        conv = self.conversations[conv_number - 1]
        print(f"\n📦 Downloading files from conversation: {conv.formatted_title(60)}")

        try:
            if self.api is None:
                print("✗ API not initialized")
                return

            # Get fresh data from API
            fresh_conv_data = self.api.get_conversation(conv.id)
            if fresh_conv_data is None:
                print(f"✗ Conversation {conv.id} not found")
                return
            fresh_conv = Conversation.from_api_response(fresh_conv_data)

            # Get list of changed files
            print("🔍 Fetching list of changed files...")

            # Extract runtime base URL from conversation URL
            runtime_url = None
            if fresh_conv.url:
                from urllib.parse import urlparse

                parsed_url = urlparse(fresh_conv.url)
                runtime_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            changes = self.api.get_conversation_changes(
                fresh_conv.id, runtime_url, fresh_conv.session_api_key
            )

            if not changes:
                print("ℹ️  No changed files found in this conversation.")
                return

            print(f"📄 Found {len(changes)} changed files")

            # Create temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                downloaded_files = []

                # Download each file
                for i, change in enumerate(changes, 1):
                    file_path = change["path"]
                    status = change["status"]

                    # Skip deleted files
                    if status == "D":
                        print(
                            f"  {i:2d}/{len(changes)} ⏭️  Skipping deleted file: "
                            f"{file_path}"
                        )
                        continue

                    print(f"  {i:2d}/{len(changes)} ⬇️  Downloading: {file_path}")

                    try:
                        # Get file content
                        content = self.api.get_file_content(
                            fresh_conv.id,
                            file_path,
                            runtime_url,
                            fresh_conv.session_api_key,
                        )

                        if content is None:
                            print(f"      ⚠️  File not found: {file_path}")
                            continue

                        # Create directory structure in temp folder
                        file_temp_path = temp_path / file_path
                        file_temp_path.parent.mkdir(parents=True, exist_ok=True)

                        # Write file content
                        with open(file_temp_path, "w", encoding="utf-8") as f:
                            f.write(content)

                        downloaded_files.append(file_path)

                    except Exception as e:
                        print(f"      ⚠️  Failed to download {file_path}: {e}")
                        continue

                if not downloaded_files:
                    print("❌ No files were successfully downloaded.")
                    return

                # Create zip file with unique name
                base_name = f"conversation-{conv.short_id()}"
                zip_path = self._get_unique_zip_path(base_name)

                print(f"📦 Creating zip file: {zip_path.name}")

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in downloaded_files:
                        file_temp_path = temp_path / file_path
                        if file_temp_path.exists():
                            zipf.write(file_temp_path, file_path)

                print(f"✅ Successfully created zip file: {zip_path}")
                print(
                    f"📊 Contains {len(downloaded_files)} files "
                    f"({zip_path.stat().st_size:,} bytes)"
                )

        except Exception as e:
            print(f"❌ Failed to download files: {e}")

    def _get_unique_zip_path(self, base_name: str) -> Path:
        """Generate a unique zip file path to avoid overwrites"""
        cwd = Path.cwd()
        zip_path = cwd / f"{base_name}.zip"

        if not zip_path.exists():
            return zip_path

        # Find unique name with counter
        counter = 1
        while True:
            zip_path = cwd / f"{base_name} ({counter}).zip"
            if not zip_path.exists():
                return zip_path
            counter += 1

    def download_trajectory(self, conv_number: int) -> None:
        """Download trajectory data from a conversation as JSON file"""
        if not (1 <= conv_number <= len(self.conversations)):
            print(f"Invalid conversation number: {conv_number}")
            return

        conv = self.conversations[conv_number - 1]
        print(
            f"\n📊 Downloading trajectory from conversation: {conv.formatted_title(60)}"
        )

        try:
            if self.api is None:
                print("✗ API not initialized")
                return

            # Get fresh data from API
            fresh_conv_data = self.api.get_conversation(conv.id)
            if fresh_conv_data is None:
                print(f"✗ Conversation {conv.id} not found")
                return
            fresh_conv = Conversation.from_api_response(fresh_conv_data)

            # Get trajectory data from API
            print("🔍 Fetching trajectory data...")
            if (
                fresh_conv.runtime_id is None
                or fresh_conv.session_api_key is None
                or fresh_conv.url is None
            ):
                print("✗ Conversation is not active or missing runtime information")
                return

            # Extract base runtime URL from the full conversation URL
            if not fresh_conv.url:
                print("✗ Conversation URL is missing")
                return

            from urllib.parse import urlparse

            parsed_url = urlparse(fresh_conv.url)
            runtime_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            trajectory_data = self.api.get_trajectory(
                fresh_conv.id, runtime_url, fresh_conv.session_api_key
            )

            # Create JSON file with unique name
            base_name = f"trajectory-{conv.short_id()}"
            json_path = self._get_unique_file_path(base_name, ".json")

            print(f"💾 Creating trajectory file: {json_path.name}")

            # Write trajectory data to JSON file
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(trajectory_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Successfully created trajectory file: {json_path}")
            print(f"📊 File size: {json_path.stat().st_size:,} bytes")

        except Exception as e:
            print(f"❌ Failed to download trajectory: {e}")

    def download_workspace(self, conv_number: int) -> None:
        """Download entire workspace from a conversation as ZIP file"""
        if not (1 <= conv_number <= len(self.conversations)):
            print(f"Invalid conversation number: {conv_number}")
            return

        conv = self.conversations[conv_number - 1]
        print(
            f"\n📦 Downloading workspace from conversation: {conv.formatted_title(60)}"
        )

        try:
            if self.api is None:
                print("✗ API not initialized")
                return

            # Get fresh data from API
            fresh_conv_data = self.api.get_conversation(conv.id)
            if fresh_conv_data is None:
                print(f"✗ Conversation {conv.id} not found")
                return
            fresh_conv = Conversation.from_api_response(fresh_conv_data)

            # Download workspace archive from API
            print("🔍 Fetching workspace archive...")

            # Extract runtime base URL from conversation URL
            runtime_url = None
            if fresh_conv.url:
                from urllib.parse import urlparse

                parsed_url = urlparse(fresh_conv.url)
                runtime_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            workspace_data = self.api.download_workspace_archive(
                fresh_conv.id, runtime_url, fresh_conv.session_api_key
            )

            if workspace_data is None:
                print("✗ Failed to download workspace archive")
                return

            # Create ZIP file with unique name (API already returns ZIP data)
            base_name = f"workspace-{conv.short_id()}"
            zip_path = self._get_unique_file_path(base_name, ".zip")

            print(f"💾 Saving workspace archive: {zip_path.name}")

            # Write workspace ZIP data directly (API already returns ZIP format)
            with open(zip_path, "wb") as f:
                f.write(workspace_data)

            print(f"✅ Successfully saved workspace archive: {zip_path}")
            print(f"📊 Archive size: {zip_path.stat().st_size:,} bytes")

        except Exception as e:
            print(f"❌ Failed to download workspace: {e}")

    def _get_unique_file_path(self, base_name: str, extension: str) -> Path:
        """Generate a unique file path to avoid overwrites"""
        cwd = Path.cwd()
        file_path = cwd / f"{base_name}{extension}"

        if not file_path.exists():
            return file_path

        # Find unique name with counter
        counter = 1
        while True:
            file_path = cwd / f"{base_name} ({counter}){extension}"
            if not file_path.exists():
                return file_path
            counter += 1

    def display_conversations(self) -> None:
        """Display the current list of conversations"""
        self.formatter.clear_screen()

        # Calculate start index for numbering
        start_index = self.current_page * self.page_size

        # Format and display table
        table_lines = self.formatter.format_conversations_table(
            self.conversations, start_index
        )
        for line in table_lines:
            print(line)

        # Show pagination info
        page_info = f"Page {self.current_page + 1}"
        if self.next_page_id:
            page_info += " (more pages available)"
        print(f"\n{page_info}")

        # Show active conversations count
        active_count = sum(1 for conv in self.conversations if conv.is_active())
        print(f"Active conversations: {active_count}/{len(self.conversations)}")

        # Always show help line
        print(
            "\nCommands: r=refresh, w <num>=wake, s <num>=show details, "
            "f <num>=download files, t <num>=trajectory, a <num>=workspace, "
            "n/p=next/prev page, h=help, q=quit"
        )

    def run_interactive(self) -> None:
        """Run the interactive command loop"""
        print("\nOpenHands Conversation Manager")
        print("Type 'h' for help, 'q' to quit")

        # Load initial conversations
        if not self.load_conversations():
            return

        while True:
            self.display_conversations()

            try:
                command = input("\nCommand: ").strip().lower()

                if not command:
                    continue

                parts = command.split()
                cmd = parts[0]

                if cmd in ["q", "quit"]:
                    break
                elif cmd in ["h", "help"]:
                    help_lines = self.formatter.format_help()
                    for line in help_lines:
                        print(line)
                    input("Press Enter to continue...")
                elif cmd in ["r", "refresh"]:
                    self.refresh_conversations()
                elif cmd in ["n", "next"]:
                    self.next_page()
                elif cmd in ["p", "prev"]:
                    self.prev_page()
                elif cmd == "w" and len(parts) == 2:
                    try:
                        conv_num = int(parts[1])
                        self.wake_conversation(conv_num)
                    except ValueError:
                        print("Invalid conversation number")
                elif cmd == "s" and len(parts) == 2:
                    try:
                        conv_num = int(parts[1])
                        self.show_conversation_details(conv_num)
                        input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid conversation number")
                elif cmd == "f" and len(parts) == 2:
                    try:
                        conv_num = int(parts[1])
                        self.download_conversation_files(conv_num)
                        input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid conversation number")
                elif cmd == "t" and len(parts) == 2:
                    try:
                        conv_num = int(parts[1])
                        self.download_trajectory(conv_num)
                        input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid conversation number")
                elif cmd == "a" and len(parts) == 2:
                    try:
                        conv_num = int(parts[1])
                        self.download_workspace(conv_num)
                        input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid conversation number")
                else:
                    print("Unknown command. Type 'h' for help.")

                if cmd not in ["h", "help", "s", "f", "t", "a"]:
                    # Small delay to show status messages
                    import time

                    time.sleep(0.5)

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                input("Press Enter to continue...")


def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="OpenHands Conversation Manager")
    parser.add_argument(
        "--api-key", "-k", help="OpenHands API key (overrides environment variables)"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test mode - just list conversations once"
    )

    args = parser.parse_args()

    # Set API key if provided
    if args.api_key:
        import os

        os.environ["OH_API_KEY"] = args.api_key

    # Check for test mode
    if args.test:
        # Simple test mode - just list conversations once
        manager = ConversationManager()
        manager.initialize()
        if manager.load_conversations():
            print(f"\nLoaded {len(manager.conversations)} conversations:")
            for i, conv in enumerate(manager.conversations, 1):
                status_icon = "🟢" if conv.is_active() else "🔴"
                runtime = conv.runtime_id or "─"
                print(
                    f"{i:2d}. {conv.short_id()} {status_icon} {conv.status:8s} "
                    f"{runtime:15s} {conv.formatted_title(60)}"
                )
            print(
                f"\nActive conversations: "
                f"{sum(1 for c in manager.conversations if c.is_active())}/"
                f"{len(manager.conversations)}"
            )
        return

    manager = ConversationManager()
    manager.initialize()
    manager.run_interactive()


if __name__ == "__main__":
    main()
