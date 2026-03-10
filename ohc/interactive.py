"""
Interactive conversation manager for OpenHands.

This module provides an interactive terminal-based interface for managing
OpenHands conversations. It uses dependency injection to receive an
OpenHandsAPI instance rather than managing its own API key retrieval.
"""

import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from .api import OpenHandsAPI
from .conversation_display import Conversation, show_conversation_details


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
        """Clear the terminal screen using ANSI escape codes.

        Uses standard ANSI escape sequences instead of os.system() for:
        - Better security (no shell execution)
        - Better portability across platforms
        - Faster execution
        """
        # ANSI escape: \033[H moves cursor to home, \033[J clears from cursor to end
        print("\033[H\033[J", end="", flush=True)

    def format_conversations_table(
        self, conversations: List[Conversation], start_index: int = 0
    ) -> List[str]:
        """Format conversations as a table with proper column alignment"""
        if not conversations:
            return ["No conversations found."]

        width, _ = self.terminal_size

        # Calculate column widths based on terminal size
        # Widths: num(5) + id(10) + status(12) + runtime(17) + title(remaining)
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
    """Main conversation manager application.

    Uses dependency injection to receive an already-configured OpenHandsAPI
    instance, eliminating the need for internal API key management.
    """

    def __init__(self, api: OpenHandsAPI) -> None:
        """Initialize ConversationManager with an API client.

        Args:
            api: Pre-configured OpenHandsAPI instance
        """
        self.api = api
        self.formatter = TerminalFormatter()
        self.conversations: List[Conversation] = []
        self.current_page = 0
        self.page_size = 20
        self.next_page_id: Optional[str] = None
        self.page_ids: List[Optional[str]] = [None]  # Track page IDs for navigation

    @property
    def api_version(self) -> str:
        """Get the API version from the underlying API client."""
        return str(self.api.version)

    def load_conversations(
        self, page_id: Optional[str] = None, offset: int = 0
    ) -> bool:
        """Load conversations from API.

        Args:
            page_id: Page ID for V0 API pagination
            offset: Offset for V1 API pagination
        """
        try:
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
            # Use shared show_conversation_details function
            show_conversation_details(self.api, conv.id)
        else:
            print(f"Invalid conversation number: {conv_number}")

    def download_conversation_files(self, conv_number: int) -> None:
        """Download all changed files from a conversation as a zip file."""
        if not (1 <= conv_number <= len(self.conversations)):
            print(f"Invalid conversation number: {conv_number}")
            return

        conv = self.conversations[conv_number - 1]
        print(f"\n📦 Downloading files from conversation: {conv.formatted_title(60)}")

        try:
            # Get fresh conversation data from API
            fresh_conv = self._get_fresh_conversation(conv.id)
            if fresh_conv is None:
                return

            # Get list of changed files
            changes = self._get_changed_files(fresh_conv)
            if changes is None:
                return

            # Download files to temp directory and create zip
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                downloaded_files = self._download_files_to_temp(
                    fresh_conv, changes, temp_path
                )

                if not downloaded_files:
                    print("❌ No files were successfully downloaded.")
                    return

                self._create_zip_from_files(
                    temp_path, downloaded_files, f"conversation-{conv.short_id()}"
                )

        except Exception as e:
            print(f"❌ Failed to download files: {e}")

    def _get_fresh_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get fresh conversation data from API."""
        fresh_conv_data = self.api.get_conversation(conv_id)
        if fresh_conv_data is None:
            print(f"✗ Conversation {conv_id} not found")
            return None
        return Conversation.from_api_response(fresh_conv_data)

    def _get_changed_files(
        self, conv: Conversation
    ) -> Optional[List[dict]]:  # type: ignore[type-arg]
        """Get list of changed files for a conversation."""
        print("🔍 Fetching list of changed files...")

        runtime_url = conv.get_runtime_base_url()
        changes = self.api.get_conversation_changes(
            conv.id, runtime_url, conv.session_api_key
        )

        if not changes:
            print("ℹ️  No changed files found in this conversation.")
            return None

        print(f"📄 Found {len(changes)} changed files")
        return changes

    def _download_files_to_temp(
        self,
        conv: Conversation,
        changes: List[dict],  # type: ignore[type-arg]
        temp_path: Path,
    ) -> List[str]:
        """Download files to a temporary directory.

        Returns list of successfully downloaded file paths.
        """
        runtime_url = conv.get_runtime_base_url()
        downloaded_files = []

        for i, change in enumerate(changes, 1):
            file_path = change["path"]
            status = change["status"]

            # Skip deleted files
            if status == "D":
                print(f"  {i:2d}/{len(changes)} ⏭️  Skipping deleted file: {file_path}")
                continue

            print(f"  {i:2d}/{len(changes)} ⬇️  Downloading: {file_path}")

            try:
                content = self.api.get_file_content(
                    conv.id, file_path, runtime_url, conv.session_api_key
                )

                if content is None:
                    print(f"      ⚠️  File not found: {file_path}")
                    continue

                file_temp_path = temp_path / file_path
                file_temp_path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_temp_path, "w", encoding="utf-8") as f:
                    f.write(content)

                downloaded_files.append(file_path)

            except Exception as e:
                print(f"      ⚠️  Failed to download {file_path}: {e}")
                continue

        return downloaded_files

    def _create_zip_from_files(
        self, temp_path: Path, files: List[str], base_name: str
    ) -> Path:
        """Create a zip file from downloaded files.

        Returns the path to the created zip file.
        """
        zip_path = self._get_unique_zip_path(base_name)
        print(f"📦 Creating zip file: {zip_path.name}")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                file_temp_path = temp_path / file_path
                if file_temp_path.exists():
                    zipf.write(file_temp_path, file_path)

        print(f"✅ Successfully created zip file: {zip_path}")
        print(f"📊 Contains {len(files)} files ({zip_path.stat().st_size:,} bytes)")
        return zip_path

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
        """Download trajectory data from a conversation as JSON file."""
        if not (1 <= conv_number <= len(self.conversations)):
            print(f"Invalid conversation number: {conv_number}")
            return

        conv = self.conversations[conv_number - 1]
        print(
            f"\n📊 Downloading trajectory from conversation: {conv.formatted_title(60)}"
        )

        try:
            fresh_conv = self._get_fresh_conversation(conv.id)
            if fresh_conv is None:
                return

            # Verify conversation has required runtime information
            print("🔍 Fetching trajectory data...")
            if not self._has_runtime_info(fresh_conv):
                print("✗ Conversation is not active or missing runtime information")
                return

            runtime_url = fresh_conv.get_runtime_base_url()
            trajectory_data = self.api.get_trajectory(
                fresh_conv.id, runtime_url, fresh_conv.session_api_key
            )

            # Save trajectory to JSON file
            self._save_trajectory_file(trajectory_data, f"trajectory-{conv.short_id()}")

        except Exception as e:
            print(f"❌ Failed to download trajectory: {e}")

    def _has_runtime_info(self, conv: Conversation) -> bool:
        """Check if conversation has required runtime information."""
        return (
            conv.runtime_id is not None
            and conv.session_api_key is not None
            and conv.url is not None
        )

    def _save_trajectory_file(self, trajectory_data: dict, base_name: str) -> Path:  # type: ignore[type-arg]
        """Save trajectory data to a JSON file.

        Returns the path to the created file.
        """
        json_path = self._get_unique_file_path(base_name, ".json")
        print(f"💾 Creating trajectory file: {json_path.name}")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(trajectory_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Successfully created trajectory file: {json_path}")
        print(f"📊 File size: {json_path.stat().st_size:,} bytes")
        return json_path

    def download_workspace(self, conv_number: int) -> None:
        """Download entire workspace from a conversation as ZIP file."""
        if not (1 <= conv_number <= len(self.conversations)):
            print(f"Invalid conversation number: {conv_number}")
            return

        conv = self.conversations[conv_number - 1]
        print(
            f"\n📦 Downloading workspace from conversation: {conv.formatted_title(60)}"
        )

        try:
            fresh_conv = self._get_fresh_conversation(conv.id)
            if fresh_conv is None:
                return

            # Download workspace archive from API
            print("🔍 Fetching workspace archive...")
            runtime_url = fresh_conv.get_runtime_base_url()
            workspace_data = self.api.download_workspace_archive(
                fresh_conv.id, runtime_url, fresh_conv.session_api_key
            )

            if workspace_data is None:
                print("✗ Failed to download workspace archive")
                return

            # Save workspace archive
            self._save_workspace_archive(workspace_data, f"workspace-{conv.short_id()}")

        except Exception as e:
            print(f"❌ Failed to download workspace: {e}")

    def _save_workspace_archive(self, workspace_data: bytes, base_name: str) -> Path:
        """Save workspace archive data to a ZIP file.

        Returns the path to the created file.
        """
        zip_path = self._get_unique_file_path(base_name, ".zip")
        print(f"💾 Saving workspace archive: {zip_path.name}")

        with open(zip_path, "wb") as f:
            f.write(workspace_data)

        print(f"✅ Successfully saved workspace archive: {zip_path}")
        print(f"📊 Archive size: {zip_path.stat().st_size:,} bytes")
        return zip_path

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
        """Run the interactive command loop."""
        print("\nOpenHands Conversation Manager")
        print("Type 'h' for help, 'q' to quit")

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

                handled = self._handle_command(cmd, parts)
                if handled == "quit":
                    break
                elif handled == "unknown":
                    print("Unknown command. Type 'h' for help.")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                input("Press Enter to continue...")

    def _handle_command(self, cmd: str, parts: List[str]) -> str:
        """Handle a single command.

        Returns:
            'quit' if user wants to exit
            'handled' if command was processed
            'unknown' if command was not recognized
        """
        # Quit commands
        if cmd in ["q", "quit"]:
            return "quit"

        # Simple commands (no argument required)
        simple_commands = {
            "h": self._show_help,
            "help": self._show_help,
            "r": self.refresh_conversations,
            "refresh": self.refresh_conversations,
            "n": self.next_page,
            "next": self.next_page,
            "p": self.prev_page,
            "prev": self.prev_page,
        }

        if cmd in simple_commands:
            simple_commands[cmd]()
            if cmd not in ["h", "help"]:
                time.sleep(0.5)
            return "handled"

        # Commands that take a conversation number: (method, wait_after)
        numbered_commands = {
            "w": (self.wake_conversation, False),
            "s": (self.show_conversation_details, True),
            "f": (self.download_conversation_files, True),
            "t": (self.download_trajectory, True),
            "a": (self.download_workspace, True),
        }

        if cmd in numbered_commands and len(parts) == 2:
            return self._handle_numbered_command(cmd, parts[1], numbered_commands[cmd])

        return "unknown"

    def _handle_numbered_command(
        self, cmd: str, arg: str, handler: tuple  # type: ignore[type-arg]
    ) -> str:
        """Handle a command that takes a conversation number argument."""
        method, wait_after = handler
        try:
            conv_num = int(arg)
            method(conv_num)
            if wait_after:
                input("Press Enter to continue...")
            else:
                time.sleep(0.5)
        except ValueError:
            print("Invalid conversation number")
        return "handled"

    def _show_help(self) -> None:
        """Display help text."""
        for line in self.formatter.format_help():
            print(line)
        input("Press Enter to continue...")
