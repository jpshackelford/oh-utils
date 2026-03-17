"""
Tests for interactive conversation manager functionality.

Tests the ohc.interactive module including:
- TerminalFormatter
- ConversationManager

Note: Conversation dataclass tests are in test_conversation_display.py
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from ohc_cli.conversation_display import Conversation
from ohc_cli.interactive import ConversationManager, TerminalFormatter


class TestTerminalFormatter:
    """Test terminal formatting functionality."""

    def test_init(self):
        """Test TerminalFormatter initialization."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = MagicMock(columns=120, lines=30)
            formatter = TerminalFormatter()
            assert formatter.terminal_size == (120, 30)

    def test_get_terminal_size_fallback(self):
        """Test terminal size fallback when shutil fails."""
        with patch("shutil.get_terminal_size", side_effect=Exception("Terminal error")):
            formatter = TerminalFormatter()
            assert formatter.terminal_size == (80, 24)

    def test_clear_screen_uses_ansi(self):
        """Test clear screen uses ANSI escape codes."""
        with patch("builtins.print") as mock_print:
            formatter = TerminalFormatter()
            formatter.clear_screen()
            mock_print.assert_called_once_with("\033[H\033[J", end="", flush=True)

    def test_format_conversations_table_empty(self):
        """Test formatting empty conversation list."""
        formatter = TerminalFormatter()
        result = formatter.format_conversations_table([])
        assert result == ["No conversations found."]

    def test_format_conversations_table_narrow_terminal(self):
        """Test formatting conversations for narrow terminal."""
        formatter = TerminalFormatter()
        formatter.terminal_size = (50, 24)

        conv = Conversation(
            id="test-conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        result = formatter.format_conversations_table([conv])
        assert len(result) > 1
        assert "1. test-con - RUNNING" in result[0]
        assert "Runtime: runtime-123" in result[2]

    def test_format_conversations_table_wide_terminal(self):
        """Test formatting conversations for wide terminal."""
        formatter = TerminalFormatter()
        formatter.terminal_size = (120, 30)

        conv = Conversation(
            id="test-conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        result = formatter.format_conversations_table([conv])
        assert len(result) >= 3
        assert "ID" in result[0]
        assert "Status" in result[0]
        assert "test-con" in result[2]

    def test_format_help(self):
        """Test help formatting."""
        formatter = TerminalFormatter()
        help_lines = formatter.format_help()

        assert isinstance(help_lines, list)
        assert len(help_lines) > 0
        assert "Commands:" in help_lines
        assert any("refresh" in line for line in help_lines)
        assert any("Wake up conversation" in line for line in help_lines)


class TestConversationManager:
    """Test ConversationManager functionality with dependency injection."""

    def _create_mock_api(self) -> MagicMock:
        """Create a mock API instance."""
        mock_api = MagicMock()
        mock_api.version = "v0"
        return mock_api

    def test_init_with_api(self):
        """Test ConversationManager initialization with API instance."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)

        assert manager.api == mock_api
        assert manager.conversations == []
        assert manager.current_page == 0
        assert manager.page_size == 20
        assert manager.next_page_id is None
        assert manager.page_ids == [None]

    def test_api_version_property(self):
        """Test api_version property returns API's version."""
        mock_api = self._create_mock_api()
        mock_api.version = "v1"

        manager = ConversationManager(mock_api)
        assert manager.api_version == "v1"

    def test_load_conversations_success(self):
        """Test successful conversation loading."""
        mock_api = self._create_mock_api()
        mock_api.search_conversations.return_value = {
            "results": [
                {
                    "conversation_id": "conv-123",
                    "title": "Test Conversation",
                    "status": "RUNNING",
                    "runtime_status": "READY",
                    "url": "https://example.com/conv-123",
                    "session_api_key": "session-key",
                    "last_updated_at": "2024-01-15T10:30:00Z",
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ],
            "next_page_id": "next-page-123",
        }

        manager = ConversationManager(mock_api)
        result = manager.load_conversations()

        assert result is True
        assert len(manager.conversations) == 1
        assert manager.conversations[0].id == "conv-123"
        # Note: next_page_id is only set for v0 API and may be None for small result sets

    def test_load_conversations_exception(self):
        """Test conversation loading handles exceptions."""
        mock_api = self._create_mock_api()
        mock_api.search_conversations.side_effect = Exception("API error")

        manager = ConversationManager(mock_api)

        with patch("builtins.print") as mock_print:
            result = manager.load_conversations()

        assert result is False
        mock_print.assert_called_with("✗ Failed to load conversations: API error")

    def test_load_conversations_v1_pagination(self):
        """Test conversation loading with V1 API pagination."""
        mock_api = self._create_mock_api()
        mock_api.version = "v1"
        mock_api.search_conversations.return_value = {
            "results": [{"conversation_id": f"conv-{i}"} for i in range(20)],
        }

        manager = ConversationManager(mock_api)
        result = manager.load_conversations()

        assert result is True
        # V1 pagination sets "more" when result count equals page_size

    def test_refresh_conversations_success(self):
        """Test successful conversation refresh."""
        mock_api = self._create_mock_api()
        mock_api.search_conversations.return_value = {"results": []}

        manager = ConversationManager(mock_api)
        manager.page_ids = [None, "page-2"]
        manager.current_page = 1

        with patch("builtins.print") as mock_print:
            manager.refresh_conversations()

        mock_print.assert_called_with("✓ Conversations refreshed")

    def test_next_page_success(self):
        """Test moving to next page."""
        mock_api = self._create_mock_api()
        mock_api.search_conversations.return_value = {
            "results": [],
            "next_page_id": "page-3",
        }

        manager = ConversationManager(mock_api)
        manager.next_page_id = "page-2"

        with patch("builtins.print") as mock_print:
            manager.next_page()

        assert manager.current_page == 1
        mock_print.assert_called_with("✓ Moved to page 2")

    def test_next_page_no_more(self):
        """Test next page when no more pages available."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.next_page_id = None

        with patch("builtins.print") as mock_print:
            manager.next_page()

        mock_print.assert_called_with("No more pages available")

    def test_prev_page_success(self):
        """Test moving to previous page."""
        mock_api = self._create_mock_api()
        mock_api.search_conversations.return_value = {"results": []}

        manager = ConversationManager(mock_api)
        manager.current_page = 1
        manager.page_ids = [None, "page-2"]

        with patch("builtins.print") as mock_print:
            manager.prev_page()

        assert manager.current_page == 0
        mock_print.assert_called_with("✓ Moved to page 1")

    def test_prev_page_already_first(self):
        """Test prev page when already on first page."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.current_page = 0

        with patch("builtins.print") as mock_print:
            manager.prev_page()

        mock_print.assert_called_with("Already on first page")

    def test_wake_conversation_success(self):
        """Test waking up a conversation."""
        mock_api = self._create_mock_api()
        mock_api.search_conversations.return_value = {"results": []}

        manager = ConversationManager(mock_api)
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        manager.conversations = [conv]

        with patch("builtins.print"):
            manager.wake_conversation(1)

        mock_api.start_conversation.assert_called_once_with("conv-123")

    def test_wake_conversation_invalid_number(self):
        """Test waking with invalid conversation number."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.conversations = []

        with patch("builtins.print") as mock_print, patch("builtins.input"):
            manager.wake_conversation(1)

        mock_print.assert_any_call("Invalid conversation number: 1")

    def test_show_conversation_details_success(self):
        """Test showing conversation details."""
        mock_api = self._create_mock_api()
        mock_api.get_conversation.return_value = {
            "conversation_id": "conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime-123.example.com/conv/conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }
        mock_api.get_conversation_changes.return_value = [
            {"path": "test.py", "status": "M"}
        ]

        manager = ConversationManager(mock_api)
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key="session-key",
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://runtime-123.example.com/conv/conv-123",
        )
        manager.conversations = [conv]

        with patch("builtins.print"):
            manager.show_conversation_details(1)

        mock_api.get_conversation.assert_called_once_with("conv-123")

    def test_show_conversation_details_invalid_number(self):
        """Test showing details with invalid conversation number."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.conversations = []

        with patch("builtins.print") as mock_print:
            manager.show_conversation_details(1)

        mock_print.assert_called_with("Invalid conversation number: 1")

    def test_download_conversation_files_invalid_number(self):
        """Test download files with invalid conversation number."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.conversations = []

        with patch("builtins.print") as mock_print:
            manager.download_conversation_files(1)

        mock_print.assert_called_with("Invalid conversation number: 1")

    def test_download_conversation_files_success(self, tmp_path: Path):
        """Test successful download and zip creation."""
        mock_api = self._create_mock_api()
        mock_api.get_conversation.return_value = {
            "conversation_id": "conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "url": "https://runtime.example.com/api/conversations/conv-123",
            "session_api_key": "session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }
        mock_api.get_conversation_changes.return_value = [
            {"path": "src/main.py", "status": "M"},
            {"path": "deleted.txt", "status": "D"},
        ]
        mock_api.get_file_content.return_value = "print('hello world')"

        manager = ConversationManager(mock_api)
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key="session-key",
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://runtime.example.com/api/conversations/conv-123",
        )
        manager.conversations = [conv]

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("builtins.print"):
                manager.download_conversation_files(1)

        # Verify zip was created
        zip_files = list(tmp_path.glob("*.zip"))
        assert len(zip_files) == 1
        assert "conv-123" in zip_files[0].name

        # Verify zip contents
        import zipfile

        with zipfile.ZipFile(zip_files[0], "r") as zipf:
            assert "src/main.py" in zipf.namelist()
            assert "deleted.txt" not in zipf.namelist()

    def test_download_conversation_files_no_changes(self):
        """Test download when no changed files exist."""
        mock_api = self._create_mock_api()
        mock_api.get_conversation.return_value = {
            "conversation_id": "conv-123",
            "title": "Test Conversation",
            "status": "RUNNING",
            "url": "https://runtime.example.com/api/conversations/conv-123",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }
        mock_api.get_conversation_changes.return_value = []

        manager = ConversationManager(mock_api)
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://runtime.example.com/api/conversations/conv-123",
        )
        manager.conversations = [conv]

        with patch("builtins.print") as mock_print:
            manager.download_conversation_files(1)

        assert any(
            "No changed files" in str(call) for call in mock_print.call_args_list
        )

    def test_get_fresh_conversation_not_found(self):
        """Test _get_fresh_conversation when conversation not found."""
        mock_api = self._create_mock_api()
        mock_api.get_conversation.return_value = None

        manager = ConversationManager(mock_api)

        with patch("builtins.print") as mock_print:
            result = manager._get_fresh_conversation("conv-123")

        assert result is None
        mock_print.assert_called_with("✗ Conversation conv-123 not found")

    def test_has_runtime_info(self):
        """Test _has_runtime_info helper method."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)

        active_conv = Conversation(
            id="conv-123",
            title="Active",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key="session-key",
            last_updated="",
            created_at="",
            url="https://example.com",
        )
        assert manager._has_runtime_info(active_conv) is True

        inactive_conv = Conversation(
            id="conv-456",
            title="Inactive",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="",
            created_at="",
            url=None,
        )
        assert manager._has_runtime_info(inactive_conv) is False

    def test_download_trajectory_invalid_number(self):
        """Test download trajectory with invalid conversation number."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.conversations = []

        with patch("builtins.print") as mock_print:
            manager.download_trajectory(1)

        mock_print.assert_called_with("Invalid conversation number: 1")

    def test_download_workspace_invalid_number(self):
        """Test download workspace with invalid conversation number."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.conversations = []

        with patch("builtins.print") as mock_print:
            manager.download_workspace(1)

        mock_print.assert_called_with("Invalid conversation number: 1")

    def test_get_unique_zip_path_no_conflict(self):
        """Test getting unique zip path when no conflict exists."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test")
            with patch("pathlib.Path.exists", return_value=False):
                result = manager._get_unique_zip_path("test-file")

        assert result == Path("/test/test-file.zip")

    def test_get_unique_zip_path_with_conflict(self):
        """Test getting unique zip path when conflicts exist."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test")

            def mock_exists(self: Path) -> bool:
                return str(self).endswith("test-file.zip") or str(self).endswith(
                    "test-file (1).zip"
                )

            with patch("pathlib.Path.exists", mock_exists):
                result = manager._get_unique_zip_path("test-file")

        assert result == Path("/test/test-file (2).zip")

    def test_get_unique_file_path(self):
        """Test getting unique file path for any extension."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test")
            with patch("pathlib.Path.exists", return_value=False):
                result = manager._get_unique_file_path("test-file", ".json")

        assert result == Path("/test/test-file.json")

    def test_display_conversations(self):
        """Test displaying conversations."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)

        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key="session-key",
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://example.com/conv-123",
        )
        manager.conversations = [conv]
        manager.current_page = 0
        manager.page_size = 20
        manager.next_page_id = "page-2"

        with patch("builtins.print") as mock_print:
            manager.display_conversations()

        assert mock_print.called
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Page 1" in call for call in print_calls)
        assert any("Active conversations: 1/1" in call for call in print_calls)

    def test_display_conversations_no_more_pages(self):
        """Test displaying conversations with no more pages."""
        mock_api = self._create_mock_api()
        manager = ConversationManager(mock_api)
        manager.conversations = []
        manager.current_page = 0
        manager.page_size = 20
        manager.next_page_id = None

        with patch("builtins.print") as mock_print:
            manager.display_conversations()

        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Page 1" in call for call in print_calls)
        assert any("Active conversations: 0/0" in call for call in print_calls)


class TestConversationStatusDisplay:
    """Test conversation status display methods through ConversationManager."""

    def test_conversation_status_display_stopped(self):
        """Test conversation status display for STOPPED status."""
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        assert conv.status_display() == "🔴 STOPPED"

    def test_conversation_status_display_pending(self):
        """Test conversation status display for pending status."""
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="PENDING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        assert conv.status_display() == "🟡 PENDING"

    def test_conversation_status_display_running(self):
        """Test conversation status display for active running."""
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        assert conv.status_display() == "🟢 RUNNING"
