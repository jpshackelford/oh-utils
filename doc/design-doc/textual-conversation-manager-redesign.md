# Textual-Based Conversation Manager Redesign

## 1. Introduction

### 1.1 Problem Statement

The current OpenHands conversation manager provides basic functionality for listing, managing, and interacting with conversations through a traditional command-line interface. However, it suffers from several usability limitations:

- **Manual table formatting and pagination**: Users must manually navigate pages and refresh data
- **Command parsing complexity**: Users must remember specific commands (`w 3`, `s 1`, etc.) for basic operations
- **Limited visual feedback**: Status indicators are text-based with minimal visual distinction
- **Sequential operations**: API calls block the interface, creating poor user experience
- **Information density**: Limited screen real estate usage with basic text formatting
- **No real-time updates**: Users must manually refresh to see status changes

These limitations create friction in the user experience and reduce productivity when managing multiple conversations and their associated files and workspaces.

### 1.2 Proposed Solution

We propose redesigning the conversation manager using Textual, a modern Python framework for building rich terminal user interfaces. This redesign will transform the experience from a basic CLI tool to a sophisticated, interactive terminal application that provides:

- **Rich visual interface** with professional appearance and intuitive navigation
- **Real-time updates** with automatic refresh and live status indicators
- **Interactive widgets** including sortable tables, file trees, and progress bars
- **Multi-pane layout** for efficient information display and workflow
- **Background operations** with non-blocking API calls and download management
- **Enhanced user feedback** through modal dialogs, progress indicators, and visual confirmations

The solution maintains the terminal-based workflow while dramatically improving usability, information density, and user experience. Users will benefit from mouse and keyboard interaction, visual feedback, and modern UI paradigms while retaining the efficiency of terminal-based tools.

**Trade-offs**: The redesign introduces a dependency on Textual and increases complexity compared to the simple CLI approach. However, the significant UX improvements and maintainability benefits of the component-based architecture justify this trade-off.

## 2. User Interface

### 2.1 Main Application Layout

The redesigned interface features a multi-pane layout optimized for conversation management workflows:

```
┌─ OpenHands Conversation Manager ─────────────────────────────────┐
│ 🔄 Auto-refresh: ON │ 📡 API Status: Connected │ ⌨️  Press F1 for help │
├─────────────────────┬─────────────────────────────────────────────┤
│ 📋 Conversations    │ 📄 Conversation Details                     │
│ ┌─────────────────┐ │ ┌─────────────────────────────────────────┐ │
│ │ 🟢 chat-app     │ │ │ Title: Build a chat application         │ │
│ │ 🔴 api-server   │ │ │ Status: 🟢 RUNNING                      │ │
│ │ 🟡 data-proc    │ │ │ Runtime: work-1-abc123                  │ │
│ │ 🟢 ml-model     │ │ │ Created: 2024-12-01 10:30 AM           │ │
│ │ 🔴 web-scraper  │ │ │ Last Updated: 2024-12-01 2:15 PM       │ │
│ │ ...             │ │ │                                         │ │
│ └─────────────────┘ │ │ 📁 Changed Files (5):                   │ │
│                     │ │ ├── 📄 app.py (Modified)                │ │
│ 🔍 Search: [____]   │ │ ├── 📄 config.json (Added)              │ │
│ 📊 Filter: [All ▼] │ │ ├── 📁 templates/                       │ │
│                     │ │ │   └── 📄 index.html (Modified)        │ │
│ ⚡ Quick Actions:   │ │ └── 📄 requirements.txt (Modified)      │ │
│ [🚀 Wake] [📥 Down] │ │                                         │ │
│ [📋 Details]        │ │ 💬 Recent Messages:                     │ │
│                     │ │ ┌─────────────────────────────────────┐ │ │
│                     │ │ │ User: Add authentication system     │ │ │
│                     │ │ │ Assistant: I'll implement JWT...    │ │ │
│                     │ │ │ User: Also add rate limiting        │ │ │
│                     │ │ └─────────────────────────────────────┘ │ │
├─────────────────────┴─────────────────────────────────────────────┤
│ F1:Help F2:Refresh F3:Search F4:Filter F5:Wake F6:Download F10:Quit│
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 User Workflow Examples

**Scenario 1: Viewing and Waking a Conversation**
1. User launches the application: `uv run oh-conversation-manager`
2. Application loads with conversation list automatically populated
3. User navigates with arrow keys or clicks on a conversation
4. Details panel updates automatically showing conversation information
5. User presses `F5` or clicks "Wake" button to start the conversation
6. Modal dialog confirms the action with progress indicator
7. Conversation status updates to "RUNNING" with green indicator

**Scenario 2: Downloading Changed Files**
1. User selects a conversation from the list
2. Details panel shows changed files in an expandable tree view
3. User presses `F6` or clicks "Download" button
4. Download manager modal appears with progress bar
5. Files download in background with real-time progress updates
6. Completion notification shows download location and file count

**Scenario 3: Searching and Filtering**
1. User presses `F3` or clicks in search box
2. Types search term (e.g., "chat")
3. Conversation list filters in real-time as user types
4. Matching conversations highlighted with search terms emphasized
5. Filter dropdown allows additional filtering by status, date, etc.

## 3. Other Context

### 3.1 Textual Framework Overview

Textual is a modern Python framework for building rich terminal user interfaces that provides:

- **Rich widgets**: DataTable, Tree, Input, Button, ProgressBar, Modal, etc.
- **CSS-like styling**: External `.tcss` files for layout and appearance
- **Reactive programming**: Automatic UI updates when data changes
- **Async support**: Non-blocking operations with `@work` decorator
- **Event system**: Mouse and keyboard event handling
- **Layout system**: Flexible containers and positioning

Key concepts:
- **App**: Main application class that manages the interface
- **Widget**: UI components that can be composed together
- **Reactive**: Variables that automatically trigger UI updates when changed
- **Compose**: Method that defines widget hierarchy and layout
- **CSS**: Styling system using familiar CSS-like syntax

### 3.2 Integration with Existing API

The redesign will leverage the existing `OpenHandsAPI` class and conversation management logic while replacing the presentation layer. The core API functionality remains unchanged, ensuring compatibility with existing backend systems.

## 4. Technical Design

### 4.1 Application Architecture

The redesigned application follows a component-based architecture with clear separation of concerns:

```python
from textual.app import App
from textual.reactive import reactive
from textual.widgets import DataTable, Tree, Input, Button, Static
from textual.containers import Container, Horizontal, Vertical

class ConversationManagerApp(App):
    """Main Textual application for conversation management"""
    
    CSS_PATH = "conversation_manager.tcss"
    
    # Reactive state
    conversations = reactive([])
    selected_conversation = reactive(None)
    search_term = reactive("")
    auto_refresh = reactive(True)
    
    def compose(self) -> ComposeResult:
        """Build the UI layout"""
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield ConversationList(id="conversation-list")
                yield SearchInput(id="search")
                yield ActionButtons(id="actions")
            with Vertical(id="main-content"):
                yield ConversationDetails(id="details")
        yield Footer()
```

### 4.2 Core Components

#### 4.2.1 Conversation List Component

```python
class ConversationList(DataTable):
    """Interactive table of conversations with sorting and filtering"""
    
    def on_mount(self) -> None:
        """Initialize the table structure"""
        self.add_columns("Status", "ID", "Title", "Runtime", "Updated")
        self.cursor_type = "row"
        self.zebra_stripes = True
    
    def update_conversations(self, conversations: List[Conversation]) -> None:
        """Update table with new conversation data"""
        self.clear()
        for conv in conversations:
            self.add_row(
                conv.status_display(),
                conv.short_id(),
                conv.formatted_title(40),
                conv.runtime_id or "─",
                conv.last_updated
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        self.app.selected_conversation = self.conversations[event.row_index]
```

#### 4.2.2 Conversation Details Component

```python
class ConversationDetails(Container):
    """Detailed view of selected conversation"""
    
    def compose(self) -> ComposeResult:
        yield Static(id="conversation-info")
        yield ConversationFileTree(id="file-tree")
        yield MessageHistory(id="messages")
    
    def watch_selected_conversation(self, conversation: Conversation) -> None:
        """Update details when conversation selection changes"""
        if conversation:
            self.query_one("#conversation-info").update(
                self.format_conversation_info(conversation)
            )
            self.query_one("#file-tree").load_files(conversation.id)
```

#### 4.2.3 File Tree Component

```python
class ConversationFileTree(Tree):
    """Tree view of changed files in a conversation"""
    
    def load_files(self, conversation_id: str) -> None:
        """Load and display changed files"""
        self.load_file_changes(conversation_id)
    
    @work(exclusive=True)
    async def load_file_changes(self, conversation_id: str) -> None:
        """Background worker to fetch file changes"""
        try:
            changes = await self.app.api.get_conversation_changes(conversation_id)
            self.populate_tree(changes)
        except Exception as e:
            self.app.notify(f"Failed to load files: {e}", severity="error")
```

### 4.3 Background Operations

#### 4.3.1 Auto-refresh System

```python
class ConversationManagerApp(App):
    
    @work(exclusive=True)
    async def auto_refresh_conversations(self) -> None:
        """Background worker for automatic conversation refresh"""
        while self.auto_refresh:
            try:
                conversations = await self.api.search_conversations()
                self.conversations = [
                    Conversation.from_api_response(data) 
                    for data in conversations.get("results", [])
                ]
                await asyncio.sleep(30)  # Refresh every 30 seconds
            except Exception as e:
                self.notify(f"Auto-refresh failed: {e}", severity="warning")
                await asyncio.sleep(60)  # Retry after 1 minute on error
```

#### 4.3.2 Download Manager

```python
class DownloadManager(Container):
    """Modal dialog for managing file downloads"""
    
    def compose(self) -> ComposeResult:
        yield Static("Downloading files...", id="status")
        yield ProgressBar(id="progress")
        yield Button("Cancel", id="cancel")
    
    @work(exclusive=True)
    async def download_files(self, conversation_id: str) -> None:
        """Background download with progress updates"""
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Static)
        
        try:
            files = await self.app.api.get_conversation_changes(conversation_id)
            progress.total = len(files)
            
            for i, file_info in enumerate(files):
                status.update(f"Downloading {file_info['path']}...")
                await self.download_single_file(file_info)
                progress.advance(1)
                
            self.app.notify("Download completed successfully!")
            self.dismiss()
        except Exception as e:
            self.app.notify(f"Download failed: {e}", severity="error")
```

### 4.4 Styling and Theming

#### 4.4.1 CSS Styling

```css
/* conversation_manager.tcss */

ConversationManagerApp {
    layout: grid;
    grid-size: 2 1;
    grid-columns: 1fr 2fr;
}

#sidebar {
    background: $surface;
    border-right: solid $primary;
    padding: 1;
}

#conversation-list {
    height: 1fr;
    border: solid $primary;
}

#conversation-list:focus {
    border: solid $accent;
}

#main-content {
    padding: 1;
}

#details {
    height: 1fr;
    border: solid $primary;
}

.status-running {
    color: $success;
}

.status-stopped {
    color: $error;
}

.status-unknown {
    color: $warning;
}
```

### 4.5 Error Handling and User Feedback

#### 4.5.1 Modal Dialogs

```python
class ErrorDialog(Container):
    """Modal dialog for error display and recovery"""
    
    def __init__(self, title: str, message: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.message = message
    
    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="dialog-title")
        yield Static(self.message, classes="dialog-message")
        with Horizontal(classes="dialog-buttons"):
            yield Button("Retry", id="retry", variant="primary")
            yield Button("Cancel", id="cancel")
```

#### 4.5.2 Notification System

```python
class ConversationManagerApp(App):
    
    def notify_success(self, message: str) -> None:
        """Show success notification"""
        self.notify(message, severity="information", timeout=3.0)
    
    def notify_error(self, message: str, exception: Exception = None) -> None:
        """Show error notification with optional details"""
        if exception:
            self.push_screen(ErrorDialog(
                "Operation Failed", 
                f"{message}\n\nDetails: {str(exception)}"
            ))
        else:
            self.notify(message, severity="error", timeout=5.0)
```

## 5. Implementation Plan

**General Acceptance Criteria:**
- All code passes ruff linting and mypy type checking
- Comprehensive test coverage for new components
- Existing API integration tests continue to pass
- Manual testing confirms all user workflows function correctly
- Performance testing shows responsive UI with large conversation lists

### 5.1 Foundation and Core Layout (M1)

Establish the basic Textual application structure and main layout components.

#### 5.1.1 Main Application Framework
- [ ] `conversation_manager/textual_app.py` - Main Textual application class
- [ ] `conversation_manager/textual_app.tcss` - Base CSS styling
- [ ] `tests/test_textual_app.py` - Basic application tests

#### 5.1.2 Layout Components
- [ ] `conversation_manager/components/layout.py` - Header, Footer, main containers
- [ ] `conversation_manager/components/conversation_list.py` - DataTable for conversations
- [ ] `tests/test_components.py` - Component unit tests

**Demo Goal**: Launch application with basic layout showing conversation list and empty details panel.

### 5.2 Interactive Conversation List (M2)

Implement the core conversation list functionality with selection and basic operations.

#### 5.2.1 Data Integration
- [ ] `conversation_manager/components/conversation_list.py` - Enhanced DataTable with API integration
- [ ] `conversation_manager/models/textual_conversation.py` - Textual-specific conversation model
- [ ] `tests/test_conversation_list.py` - List functionality tests

#### 5.2.2 Selection and Navigation
- [ ] `conversation_manager/components/conversation_details.py` - Details panel component
- [ ] `conversation_manager/components/search.py` - Search input component
- [ ] `tests/test_navigation.py` - Navigation and selection tests

**Demo Goal**: Users can view conversations, select them with keyboard/mouse, and see basic details.

### 5.3 Background Operations and Real-time Updates (M3)

Add auto-refresh, background API calls, and non-blocking operations.

#### 5.3.1 Background Workers
- [ ] `conversation_manager/workers/refresh_worker.py` - Auto-refresh implementation
- [ ] `conversation_manager/workers/api_worker.py` - Background API operations
- [ ] `tests/test_workers.py` - Worker functionality tests

#### 5.3.2 Real-time UI Updates
- [ ] `conversation_manager/components/status_indicators.py` - Live status updates
- [ ] `conversation_manager/reactive/conversation_state.py` - Reactive state management
- [ ] `tests/test_reactive_updates.py` - Real-time update tests

**Demo Goal**: Conversations auto-refresh every 30 seconds, status indicators update live, operations don't block UI.

### 5.4 File Management and Downloads (M4)

Implement file tree view, download management, and progress tracking.

#### 5.4.1 File Tree Component
- [ ] `conversation_manager/components/file_tree.py` - Tree view for changed files
- [ ] `conversation_manager/components/file_preview.py` - File content preview with syntax highlighting
- [ ] `tests/test_file_components.py` - File component tests

#### 5.4.2 Download Manager
- [ ] `conversation_manager/components/download_manager.py` - Download modal with progress
- [ ] `conversation_manager/workers/download_worker.py` - Background download operations
- [ ] `tests/test_download_manager.py` - Download functionality tests

**Demo Goal**: Users can view changed files in tree format, download files with progress bars, preview file contents.

### 5.5 Advanced Features and Polish (M5)

Add search/filtering, modal dialogs, keyboard shortcuts, and enhanced error handling.

#### 5.5.1 Search and Filtering
- [ ] `conversation_manager/components/search_filter.py` - Advanced search and filter controls
- [ ] `conversation_manager/utils/search_utils.py` - Search logic and highlighting
- [ ] `tests/test_search_filter.py` - Search functionality tests

#### 5.5.2 Modal Dialogs and Error Handling
- [ ] `conversation_manager/components/modals.py` - Confirmation and error dialogs
- [ ] `conversation_manager/components/notifications.py` - Toast notifications and feedback
- [ ] `tests/test_modals.py` - Modal and notification tests

**Demo Goal**: Full-featured application with search, filtering, modal confirmations, comprehensive error handling, and keyboard shortcuts.

### 5.6 Integration and Migration (M6)

Integrate with existing CLI entry point and provide migration path.

#### 5.6.1 CLI Integration
- [ ] `conversation_manager/cli_integration.py` - Command-line argument handling for Textual mode
- [ ] `conversation_manager/__main__.py` - Updated entry point with mode selection
- [ ] `tests/test_cli_integration.py` - CLI integration tests

#### 5.6.2 Configuration and Settings
- [ ] `conversation_manager/config/textual_config.py` - Textual-specific configuration
- [ ] `conversation_manager/components/settings.py` - Settings dialog for customization
- [ ] `tests/test_configuration.py` - Configuration tests

**Demo Goal**: Users can launch either classic CLI mode or new Textual mode, with smooth migration path and preserved settings.