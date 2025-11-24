# OpenHands Conversation Manager

A terminal-based utility for managing OpenHands conversations with an interactive interface.

## Features

- 📋 **List conversations** with status, runtime IDs, and titles
- 🖥️ **Terminal-aware formatting** that adapts to your screen size
- 📄 **Pagination** for handling large numbers of conversations
- 🔄 **Real-time refresh** to see updated conversation states
- ⚡ **Wake up conversations** by number to start inactive ones
- 🔍 **Detailed conversation info** with full metadata
- 🎯 **Interactive commands** for easy navigation and management

## Installation

### Using uv (Recommended)

From the oh-utils directory:
```bash
uv run oh-conversation-manager
```

### Using pip

After installing the package:
```bash
oh-conversation-manager
```

Or run directly:
```bash
python3 conversation_manager/conversation_manager.py
```

## Usage

### Starting the Manager

```bash
cd oh-utils
uv run oh-conversation-manager
```

The utility will:
1. Check for an API key in the `OH_API_KEY` environment variable
2. Look for a stored API key in `~/.openhands/config.json`
3. Prompt you to enter an API key if none is found

### Interactive Commands

Once running, you can use these commands:

| Command | Description |
|---------|-------------|
| `r`, `refresh` | Refresh the current page of conversations |
| `w <num>` | Wake up conversation by number (e.g., `w 3`) |
| `s <num>` | Show detailed info for conversation (e.g., `s 1`) |
| `n`, `next` | Go to next page |
| `p`, `prev` | Go to previous page |
| `h`, `help` | Show help |
| `q`, `quit` | Exit the program |

### Display Format

The conversation list shows:
- **#**: Sequential number for easy reference
- **ID**: Short conversation ID (first 8 characters)
- **Status**: Current status with color indicators:
  - 🟢 RUNNING (active with runtime)
  - 🔴 STOPPED (inactive)
  - 🟡 Other states
- **Runtime**: Runtime ID if conversation is active
- **Title**: Conversation title (truncated to fit terminal)

### Example Session

```
OpenHands Conversation Manager
Type 'h' for help, 'q' to quit

#    ID       Status       Runtime         Title
────────────────────────────────────────────────────────────────────────
1    bbeb409a 🟢 RUNNING   hkrawbfjbtqqduhr List Last 5 Conversations via OpenHands API
2    0c32204c 🔴 STOPPED   ─               Repeatedly run ls command on non-existent file
3    1d9093df 🔴 STOPPED   ─               Clone repo, compile & run long_wait.c program

Page 1
Active conversations: 1/3

Command: w 2
Waking up conversation: Repeatedly run ls command on non-existent file
✓ Conversation started successfully
✓ Conversations refreshed

Command: s 1
Conversation Details:
  ID: bbeb409a2b68416aa0fbb669a0dd2129
  Title: List Last 5 Conversations via OpenHands API
  Status: 🟢 RUNNING
  Runtime Status: STATUS$READY
  Runtime ID: hkrawbfjbtqqduhr
  Created: 2025-11-24T12:37:52.972105Z
  Last Updated: 2025-11-24T12:41:16.683545Z
  URL: https://hkrawbfjbtqqduhr.prod-runtime.all-hands.dev/api/conversations/bbeb409a2b68416aa0fbb669a0dd2129

Press Enter to continue...
```

## Terminal Compatibility

The utility automatically adapts to your terminal size:
- **Wide terminals**: Full table format with all columns
- **Narrow terminals**: Compact format with wrapped information
- **Dynamic pagination**: Page size adjusts based on terminal height

## API Key Management

The utility supports multiple ways to provide your OpenHands API key:

1. **Environment variable**: Set `OH_API_KEY`
2. **Stored configuration**: Automatically saved to `~/.openhands/config.json`
3. **Interactive prompt**: Enter when prompted

Get your API key from: https://app.all-hands.dev/settings/api-keys

## Requirements

- Python 3.8+
- requests >= 2.25.0
- OpenHands API key with conversation access

## Error Handling

The utility includes robust error handling for:
- Network connectivity issues
- Invalid API keys
- API rate limits
- Terminal resize events
- Keyboard interrupts (Ctrl+C)

## Development

To contribute or modify the utility:

1. Clone the repository
2. Install dependencies: `uv pip install -r conversation_manager/requirements.txt`
3. Run directly: `python3 conversation_manager/conversation_manager.py`

The code is organized into several classes:
- `ConversationManager`: Main application logic
- `OpenHandsAPI`: API client for OpenHands
- `APIKeyManager`: Handles API key storage and validation
- `TerminalFormatter`: Terminal display and formatting
- `Conversation`: Data model for conversation information