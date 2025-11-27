"""
Tests for conversation manager functionality.

Tests the conversation manager module including:
- Conversation dataclass
- APIKeyManager
- TerminalFormatter
- ConversationManager (basic functionality)
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from conversation_manager.conversation_manager import (
    APIKeyManager,
    Conversation,
    ConversationManager,
    TerminalFormatter,
)


class TestConversation:
    """Test Conversation dataclass functionality."""

    def test_conversation_creation(self):
        """Test creating a Conversation instance."""
        conv = Conversation(
            id="test-id-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id="runtime-123",
            session_api_key="session-key",
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="https://example.com/conv/test-id-123",
        )

        assert conv.id == "test-id-123"
        assert conv.title == "Test Conversation"
        assert conv.status == "RUNNING"
        assert conv.runtime_status == "READY"

    def test_conversation_short_id(self):
        """Test short ID generation."""
        conv = Conversation(
            id="test-id-123456789",
            title="Test",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        short_id = conv.short_id()
        assert len(short_id) == 8
        assert short_id == "test-id-"

    def test_conversation_formatted_title(self):
        """Test title formatting with width limit."""
        conv = Conversation(
            id="test-id",
            title="This is a very long conversation title that should be truncated",
            status="RUNNING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )

        formatted = conv.formatted_title(20)
        assert len(formatted) <= 20
        assert formatted.endswith("...")

    def test_conversation_from_api_response(self):
        """Test creating Conversation from API response data."""
        api_data = {
            "conversation_id": "api-conv-123",
            "title": "API Conversation",
            "status": "RUNNING",
            "runtime_status": "READY",
            "url": "https://runtime.example.com/conv/api-conv-123",
            "session_api_key": "api-session-key",
            "last_updated_at": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:00:00Z",
        }

        conv = Conversation.from_api_response(api_data)

        assert conv.id == "api-conv-123"
        assert conv.title == "API Conversation"
        assert conv.status == "RUNNING"
        assert conv.runtime_status == "READY"
        assert conv.url == "https://runtime.example.com/conv/api-conv-123"


class TestAPIKeyManager:
    """Test API key management functionality."""

    def test_init_creates_config_dir(self):
        """Test initialization creates config directory."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path("/tmp/test-home")

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                api_manager = APIKeyManager()

                assert api_manager.config_dir == Path("/tmp/test-home/.openhands")
                mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_get_stored_key_file_not_exists(self):
        """Test getting stored key when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            api_manager = APIKeyManager()
            api_manager.config_dir = Path(temp_dir)
            api_manager.config_file = api_manager.config_dir / "config.json"

            key = api_manager.get_stored_key()

            assert key is None

    def test_get_stored_key_valid_file(self):
        """Test getting stored key from valid config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            api_manager = APIKeyManager()
            api_manager.config_dir = Path(temp_dir)
            api_manager.config_file = api_manager.config_dir / "config.json"

            config = {"api_key": "stored-test-key"}
            with open(api_manager.config_file, "w") as f:
                json.dump(config, f)

            key = api_manager.get_stored_key()

            assert key == "stored-test-key"

    def test_get_stored_key_invalid_json(self):
        """Test getting stored key with invalid JSON returns None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            api_manager = APIKeyManager()
            api_manager.config_dir = Path(temp_dir)
            api_manager.config_file = api_manager.config_dir / "config.json"

            with open(api_manager.config_file, "w") as f:
                f.write("invalid json")

            key = api_manager.get_stored_key()

            assert key is None

    def test_store_key(self):
        """Test storing API key."""
        with tempfile.TemporaryDirectory() as temp_dir:
            api_manager = APIKeyManager()
            api_manager.config_dir = Path(temp_dir)
            api_manager.config_file = api_manager.config_dir / "config.json"

            api_manager.store_key("test-api-key")

            assert api_manager.config_file.exists()

            with open(api_manager.config_file) as f:
                config = json.load(f)

            assert config["api_key"] == "test-api-key"

            # Check file permissions
            file_mode = api_manager.config_file.stat().st_mode & 0o777
            assert file_mode == 0o600

    def test_get_valid_key_from_environment(self):
        """Test getting valid key from environment variable."""
        with patch.dict(os.environ, {"OH_API_KEY": "env-test-key"}), patch(
            "conversation_manager.conversation_manager.OpenHandsAPI"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.test_connection.return_value = True
            mock_api.search_conversations.return_value = {"results": []}
            mock_api_class.return_value = mock_api

            api_manager = APIKeyManager()

            with patch("builtins.print") as mock_print:
                key = api_manager.get_valid_key()

            assert key == "env-test-key"
            mock_print.assert_called_with(
                "✓ Using API key from OH_API_KEY environment variable"
            )

    def test_get_valid_key_from_openhands_env(self):
        """Test getting valid key from OPENHANDS_API_KEY environment variable."""
        with patch.dict(
            os.environ, {"OPENHANDS_API_KEY": "openhands-env-key"}, clear=True
        ), patch(
            "conversation_manager.conversation_manager.OpenHandsAPI"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.test_connection.return_value = True
            mock_api.search_conversations.return_value = {"results": []}
            mock_api_class.return_value = mock_api

            api_manager = APIKeyManager()

            with patch("builtins.print") as mock_print:
                key = api_manager.get_valid_key()

            assert key == "openhands-env-key"
            mock_print.assert_called_with(
                "✓ Using API key from OPENHANDS_API_KEY environment variable"
            )


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

    def test_clear_screen_posix(self):
        """Test clear screen on POSIX systems."""
        with patch("os.name", "posix"), patch("os.system") as mock_system:
            formatter = TerminalFormatter()
            formatter.clear_screen()

            mock_system.assert_called_once_with("clear")

    def test_clear_screen_windows(self):
        """Test clear screen on Windows systems."""
        with patch("os.name", "nt"), patch("os.system") as mock_system:
            formatter = TerminalFormatter()
            formatter.clear_screen()

            mock_system.assert_called_once_with("cls")

    def test_format_conversations_table_empty(self):
        """Test formatting empty conversation list."""
        formatter = TerminalFormatter()

        result = formatter.format_conversations_table([])

        assert result == ["No conversations found."]

    def test_format_conversations_table_narrow_terminal(self):
        """Test formatting conversations for narrow terminal."""
        formatter = TerminalFormatter()
        formatter.terminal_size = (50, 24)  # Narrow terminal

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

        assert len(result) > 1  # Should have multiple lines for narrow format
        assert "1. test-con - RUNNING" in result[0]
        assert "Runtime: runtime-123" in result[2]

    def test_format_conversations_table_wide_terminal(self):
        """Test formatting conversations for wide terminal."""
        formatter = TerminalFormatter()
        formatter.terminal_size = (120, 30)  # Wide terminal

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

        # Should have header and conversation line
        assert len(result) >= 3
        assert "ID" in result[0]  # Header
        assert "Status" in result[0]
        assert "test-con" in result[2]  # Conversation line


class TestConversationManager:
    """Test ConversationManager basic functionality."""

    def test_init(self):
        """Test ConversationManager initialization."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"), patch(
            "conversation_manager.conversation_manager.TerminalFormatter"
        ):
            manager = ConversationManager()

            assert manager.api is None
            assert manager.conversations == []
            assert manager.current_page == 0
            assert manager.page_size == 20
            assert manager.next_page_id is None
            assert manager.page_ids == [None]

    def test_initialize_success(self):
        """Test successful initialization with valid API key."""
        with patch(
            "conversation_manager.conversation_manager.APIKeyManager"
        ) as mock_api_manager_class:
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                with patch(
                    "conversation_manager.conversation_manager.OpenHandsAPI"
                ) as mock_api_class:
                    mock_api_manager = MagicMock()
                    mock_api_manager.get_valid_key.return_value = "valid-key"
                    mock_api_manager_class.return_value = mock_api_manager

                    mock_api = MagicMock()
                    mock_api_class.return_value = mock_api

                    manager = ConversationManager()

                    with patch("builtins.print") as mock_print:
                        manager.initialize()

                    assert manager.api == mock_api
                    mock_print.assert_called_with(
                        "✓ Conversation Manager initialized successfully"
                    )

    def test_initialize_keyboard_interrupt(self):
        """Test initialization handles keyboard interrupt."""
        with patch(
            "conversation_manager.conversation_manager.APIKeyManager"
        ) as mock_api_manager_class:
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                mock_api_manager = MagicMock()
                mock_api_manager.get_valid_key.side_effect = KeyboardInterrupt()
                mock_api_manager_class.return_value = mock_api_manager

                manager = ConversationManager()

                with patch("builtins.print") as mock_print:
                    with patch("sys.exit") as mock_exit:
                        manager.initialize()

                mock_print.assert_called_with("\nExiting...")
                mock_exit.assert_called_with(1)

    def test_initialize_exception(self):
        """Test initialization handles general exceptions."""
        with patch(
            "conversation_manager.conversation_manager.APIKeyManager"
        ) as mock_api_manager_class:
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                mock_api_manager = MagicMock()
                mock_api_manager.get_valid_key.side_effect = Exception("API error")
                mock_api_manager_class.return_value = mock_api_manager

                manager = ConversationManager()

                with patch("builtins.print") as mock_print:
                    with patch("sys.exit") as mock_exit:
                        manager.initialize()

                mock_print.assert_called_with("✗ Failed to initialize: API error")
                mock_exit.assert_called_with(1)

    def test_load_conversations_no_api(self):
        """Test loading conversations when API not initialized."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()

                with patch("builtins.print") as mock_print:
                    result = manager.load_conversations()

                assert result is False
                mock_print.assert_called_with("✗ API not initialized")

    def test_load_conversations_success(self):
        """Test successful conversation loading."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
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

                manager = ConversationManager()
                manager.api = mock_api

                result = manager.load_conversations()

                assert result is True
                assert len(manager.conversations) == 1
                assert manager.conversations[0].id == "conv-123"
                assert manager.next_page_id == "next-page-123"

    def test_load_conversations_exception(self):
        """Test conversation loading handles exceptions."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.side_effect = Exception("API error")

                manager = ConversationManager()
                manager.api = mock_api

                with patch("builtins.print") as mock_print:
                    result = manager.load_conversations()

                assert result is False
                mock_print.assert_called_with(
                    "✗ Failed to load conversations: API error"
                )

    def test_refresh_conversations_success(self):
        """Test successful conversation refresh."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.return_value = {
                    "results": [],
                    "next_page_id": None,
                }

                manager = ConversationManager()
                manager.api = mock_api
                manager.page_ids = [None, "page-2"]
                manager.current_page = 1

                with patch("builtins.print") as mock_print:
                    manager.refresh_conversations()

                mock_print.assert_called_with("✓ Conversations refreshed")

    def test_refresh_conversations_failure(self):
        """Test conversation refresh failure."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.side_effect = Exception("API error")

                manager = ConversationManager()
                manager.api = mock_api

                with patch("builtins.print") as mock_print:
                    manager.refresh_conversations()

                mock_print.assert_called_with("✗ Failed to refresh conversations")

    def test_next_page_success(self):
        """Test successful next page navigation."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.return_value = {
                    "results": [],
                    "next_page_id": None,
                }

                manager = ConversationManager()
                manager.api = mock_api
                manager.next_page_id = "page-2"
                manager.page_ids = [None]
                manager.current_page = 0

                with patch("builtins.print") as mock_print:
                    manager.next_page()

                assert manager.current_page == 1
                assert len(manager.page_ids) == 2
                mock_print.assert_called_with("✓ Moved to page 2")

    def test_next_page_no_more_pages(self):
        """Test next page when no more pages available."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.next_page_id = None

                with patch("builtins.print") as mock_print:
                    manager.next_page()

                mock_print.assert_called_with("No more pages available")

    def test_next_page_load_failure(self):
        """Test next page with load failure."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.side_effect = Exception("API error")

                manager = ConversationManager()
                manager.api = mock_api
                manager.next_page_id = "page-2"
                manager.page_ids = [None]
                manager.current_page = 0

                with patch("builtins.print") as mock_print:
                    manager.next_page()

                assert manager.current_page == 0  # Should revert
                mock_print.assert_called_with("✗ Failed to load next page")

    def test_prev_page_success(self):
        """Test successful previous page navigation."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.return_value = {
                    "results": [],
                    "next_page_id": None,
                }

                manager = ConversationManager()
                manager.api = mock_api
                manager.page_ids = [None, "page-2"]
                manager.current_page = 1

                with patch("builtins.print") as mock_print:
                    manager.prev_page()

                assert manager.current_page == 0
                mock_print.assert_called_with("✓ Moved to page 1")

    def test_prev_page_first_page(self):
        """Test previous page when already on first page."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.current_page = 0

                with patch("builtins.print") as mock_print:
                    manager.prev_page()

                mock_print.assert_called_with("Already on first page")

    def test_prev_page_load_failure(self):
        """Test previous page with load failure."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.search_conversations.side_effect = Exception("API error")

                manager = ConversationManager()
                manager.api = mock_api
                manager.page_ids = [None, "page-2"]
                manager.current_page = 1

                with patch("builtins.print") as mock_print:
                    manager.prev_page()

                assert manager.current_page == 1  # Should revert
                mock_print.assert_called_with("✗ Failed to load previous page")

    def test_wake_conversation_success(self):
        """Test successful conversation wake up."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.terminal_size = (120, 30)
                mock_formatter_class.return_value = mock_formatter

                mock_api = MagicMock()
                mock_api.start_conversation.return_value = {
                    "url": "https://example.com"
                }
                mock_api.search_conversations.return_value = {
                    "results": [],
                    "next_page_id": None,
                }

                # Create a test conversation
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

                manager = ConversationManager()
                manager.api = mock_api
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.wake_conversation(1)

                mock_api.start_conversation.assert_called_once_with("conv-123")
                mock_print.assert_any_call("Waking up conversation: Test Conversation")
                mock_print.assert_any_call("✓ Conversation started successfully")

    def test_wake_conversation_no_api(self):
        """Test wake conversation when API not initialized."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
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

                manager = ConversationManager()
                manager.api = None
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.wake_conversation(1)

                mock_print.assert_called_with("✗ API not initialized")

    def test_wake_conversation_invalid_number(self):
        """Test wake conversation with invalid number."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.conversations = []

                with patch("builtins.print") as mock_print:
                    with patch("builtins.input") as mock_input:
                        manager.wake_conversation(1)

                mock_print.assert_called_with("Invalid conversation number: 1")
                mock_input.assert_called_with("Press Enter to continue...")

    def test_wake_conversation_api_error(self):
        """Test wake conversation with API error."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                mock_api = MagicMock()
                mock_api.start_conversation.side_effect = Exception("Start failed")

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

                manager = ConversationManager()
                manager.api = mock_api
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    with patch("builtins.input") as mock_input:
                        manager.wake_conversation(1)

                mock_print.assert_any_call(
                    "✗ Failed to wake conversation: Start failed"
                )
                mock_input.assert_called_with("Press Enter to continue...")

    def test_show_conversation_details_success(self):
        """Test successful conversation details display."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                mock_api = MagicMock()
                mock_api.get_conversation.return_value = {
                    "conversation_id": "conv-123",
                    "title": "Test Conversation",
                    "status": "RUNNING",
                    "runtime_status": "READY",
                    "runtime_id": "runtime-123",
                    "url": "https://example.com/conv-123",
                    "session_api_key": "session-key",
                    "last_updated_at": "2024-01-15T10:30:00Z",
                    "created_at": "2024-01-15T10:00:00Z",
                }

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

                manager = ConversationManager()
                manager.api = mock_api
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.show_conversation_details(1)

                mock_api.get_conversation.assert_called_once_with("conv-123")
                mock_print.assert_any_call("\nConversation Details:")

    def test_show_conversation_details_no_api(self):
        """Test show conversation details when API not initialized."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
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

                manager = ConversationManager()
                manager.api = None
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.show_conversation_details(1)

                mock_print.assert_called_with("✗ API not initialized")

    def test_show_conversation_details_invalid_number(self):
        """Test show conversation details with invalid number."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.conversations = []

                with patch("builtins.print") as mock_print:
                    manager.show_conversation_details(1)

                mock_print.assert_called_with("Invalid conversation number: 1")

    def test_display_conversations(self):
        """Test displaying conversations."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.format_conversations_table.return_value = [
                    "  #  ID       Title                Status",
                    "  1  conv-123 Test Conversation    RUNNING",
                ]
                mock_formatter_class.return_value = mock_formatter

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

                manager = ConversationManager()
                manager.conversations = [conv]
                manager.current_page = 0
                manager.page_size = 20
                manager.next_page_id = "page-2"

                with patch("builtins.print") as mock_print:
                    manager.display_conversations()

                mock_formatter.clear_screen.assert_called_once()
                mock_formatter.format_conversations_table.assert_called_once_with(
                    [conv], 0
                )
                mock_print.assert_any_call("  #  ID       Title                Status")
                mock_print.assert_any_call("  1  conv-123 Test Conversation    RUNNING")
                mock_print.assert_any_call("\nPage 1 (more pages available)")
                mock_print.assert_any_call("Active conversations: 1/1")

    def test_display_conversations_no_more_pages(self):
        """Test displaying conversations with no more pages."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.format_conversations_table.return_value = [
                    "No conversations"
                ]
                mock_formatter_class.return_value = mock_formatter

                manager = ConversationManager()
                manager.conversations = []
                manager.current_page = 0
                manager.page_size = 20
                manager.next_page_id = None

                with patch("builtins.print") as mock_print:
                    manager.display_conversations()

                mock_print.assert_any_call("\nPage 1")
                mock_print.assert_any_call("Active conversations: 0/0")

    def test_get_unique_zip_path_no_conflict(self):
        """Test getting unique zip path when no conflict exists."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                with patch("pathlib.Path.cwd") as mock_cwd:
                    with patch("pathlib.Path.exists", return_value=False):
                        mock_cwd.return_value = Path("/test")

                        manager = ConversationManager()
                        result = manager._get_unique_zip_path("test-file")

                        assert result == Path("/test/test-file.zip")

    def test_get_unique_zip_path_with_conflict(self):
        """Test getting unique zip path when conflicts exist."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = Path("/test")

                    # Mock exists to return True for base name and first counter, False for second
                    def mock_exists(self):
                        return bool(
                            str(self).endswith("test-file.zip")
                            or str(self).endswith("test-file (1).zip")
                        )

                    with patch("pathlib.Path.exists", mock_exists):
                        manager = ConversationManager()
                        result = manager._get_unique_zip_path("test-file")

                        assert result == Path("/test/test-file (2).zip")

    def test_download_trajectory_invalid_number(self):
        """Test download trajectory with invalid conversation number."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.conversations = []

                with patch("builtins.print") as mock_print:
                    manager.download_trajectory(1)

                mock_print.assert_called_with("Invalid conversation number: 1")

    def test_download_trajectory_no_api(self):
        """Test download trajectory when API not initialized."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
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

                manager = ConversationManager()
                manager.api = None
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.download_trajectory(1)

                mock_print.assert_any_call("✗ API not initialized")

    def test_download_workspace_invalid_number(self):
        """Test download workspace with invalid conversation number."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.conversations = []

                with patch("builtins.print") as mock_print:
                    manager.download_workspace(1)

                mock_print.assert_called_with("Invalid conversation number: 1")

    def test_download_workspace_no_api(self):
        """Test download workspace when API not initialized."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
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

                manager = ConversationManager()
                manager.api = None
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.download_workspace(1)

                mock_print.assert_any_call("✗ API not initialized")

    def test_download_conversation_files_invalid_number(self):
        """Test download conversation files with invalid conversation number."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
                manager = ConversationManager()
                manager.conversations = []

                with patch("builtins.print") as mock_print:
                    manager.download_conversation_files(1)

                mock_print.assert_called_with("Invalid conversation number: 1")

    def test_download_conversation_files_no_api(self):
        """Test download conversation files when API not initialized."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch("conversation_manager.conversation_manager.TerminalFormatter"):
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

                manager = ConversationManager()
                manager.api = None
                manager.conversations = [conv]

                with patch("builtins.print") as mock_print:
                    manager.download_conversation_files(1)

                mock_print.assert_any_call("✗ API not initialized")

    def test_format_help(self):
        """Test help formatting through formatter."""
        with patch("conversation_manager.conversation_manager.APIKeyManager"):
            with patch(
                "conversation_manager.conversation_manager.TerminalFormatter"
            ) as mock_formatter_class:
                mock_formatter = MagicMock()
                mock_formatter.format_help.return_value = [
                    "\nAvailable commands:",
                    "  r - Refresh conversation list",
                ]
                mock_formatter_class.return_value = mock_formatter

                manager = ConversationManager()
                help_lines = manager.formatter.format_help()

                assert "\nAvailable commands:" in help_lines
                assert "  r - Refresh conversation list" in help_lines

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

    def test_conversation_status_display_other(self):
        """Test conversation status display for other status."""
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

    def test_conversation_runtime_id_extraction_error(self):
        """Test runtime ID extraction with malformed URL."""
        conv = Conversation(
            id="conv-123",
            title="Test Conversation",
            status="RUNNING",
            runtime_status="READY",
            runtime_id=None,
            session_api_key="session-key",
            last_updated="2024-01-15T10:30:00Z",
            created_at="2024-01-15T10:00:00Z",
            url="malformed-url",
        )

        # This should trigger the exception handling in runtime_id property
        assert conv.runtime_id is None


class TestTerminalFormatterHelp:
    """Test TerminalFormatter help functionality."""

    def test_format_help_direct_call(self):
        """Test direct call to format_help method."""
        formatter = TerminalFormatter()
        help_lines = formatter.format_help()

        # Verify help content
        assert isinstance(help_lines, list)
        assert len(help_lines) > 0
        assert "Commands:" in help_lines
        assert any("refresh" in line for line in help_lines)
        assert any("Wake up conversation" in line for line in help_lines)


class TestConversationManagerAdditionalCoverage:
    """Additional tests to improve coverage of conversation_manager module."""

    def test_conversation_dataclass_optional_fields(self):
        """Test Conversation with minimal required fields."""
        conv = Conversation(
            id="minimal-id",
            title="Minimal",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:00:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        assert conv.id == "minimal-id"
        assert conv.runtime_id is None
        assert conv.url is None

    def test_conversation_status_stopped(self):
        """Test conversation status display for STOPPED status."""
        conv = Conversation(
            id="test-id",
            title="Test",
            status="STOPPED",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:00:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        status = conv.status_display()
        assert "STOPPED" in status
        assert "🔴" in status

    def test_conversation_status_unknown(self):
        """Test conversation status display for unknown status."""
        conv = Conversation(
            id="test-id",
            title="Test",
            status="PENDING",
            runtime_status=None,
            runtime_id=None,
            session_api_key=None,
            last_updated="2024-01-15T10:00:00Z",
            created_at="2024-01-15T10:00:00Z",
            url=None,
        )
        status = conv.status_display()
        assert "PENDING" in status
        assert "🟡" in status

    def test_manager_initialization(self):
        """Test ConversationManager initialization."""
        manager = ConversationManager()
        assert manager.api is None
        assert manager.conversations == []
        assert manager.current_page == 0
        assert manager.page_size == 20
