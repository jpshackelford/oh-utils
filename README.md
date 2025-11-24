# OpenHands Utilities

A collection of utilities for working with OpenHands (formerly All-Hands-AI / OpenDevin) API and conversations.

## Installation

### Using uv (Recommended)

Install using uv:
```bash
uv pip install -e .
```

Or run directly without installation:
```bash
# API Utility version (newer, recommended)
uv run oh-conversation-downloader

# Cloud API version (alternative)
uv run oh-conversation-downloader-cloud
```

### Using pip

```bash
pip install -e .
```

## Utilities

This repository contains three utilities for working with OpenHands conversations:

### 1. OpenHands API Utility (Recommended)

**Command:** `uv run oh-conversation-downloader`

A modern Python utility for downloading conversations and workspace files from the OpenHands Cloud API.

**Features:**
- 🔐 Secure API key management
- 📋 List all conversations with pagination
- 📦 Download workspace archives
- 📄 Download changed files from conversations
- 💬 Interactive command-line interface
- 🗂️ User-friendly conversation browsing

**Quick Start:**

Using uv (recommended):
```bash
cd oh-utils
uv run oh-conversation-downloader
```

Or after installation:
```bash
oh-conversation-downloader
```

Traditional method:
```bash
python3 openhands_api_utility/openhands_utility.py
```

See the [OpenHands API Utility README](./openhands_api_utility/README.md) for detailed usage instructions.

### 2. Conversation Downloader - Cloud API Version

**Command:** `uv run oh-conversation-downloader-cloud`

An alternative implementation with different API endpoints and features.

**Features:**
- 🔐 Secure token storage in `~/.config/openhands/api_token`
- 📋 List conversations with pagination (up to 200)
- 📦 Full workspace archive downloads
- 🔍 Recursive file scanning from `/workspace/project`
- ⚡ Progress indicators for file downloads
- 🛡️ Rate limit handling & error recovery

**Quick Start:**

Using uv (recommended):
```bash
cd oh-utils
uv run oh-conversation-downloader-cloud
```

Traditional method:
```bash
python3 conversation_downloader/openhands_conversation_downloader.py
```

See the [Conversation Downloader README](./conversation_downloader/README.md) for detailed usage instructions.

### 3. Conversation Manager

**Command:** `uv run oh-conversation-manager`

A terminal-based interactive utility for managing OpenHands conversations.

**Features:**
- 📋 List conversations with status, runtime IDs, and titles
- 🖥️ Terminal-aware formatting that adapts to screen size
- 📄 Pagination for handling large numbers of conversations
- 🔄 Real-time refresh to see updated conversation states
- ⚡ Wake up conversations by number to start inactive ones
- 🔍 Detailed conversation info with full metadata
- 🎯 Interactive commands for easy navigation and management

**Quick Start:**

Using uv (recommended):
```bash
cd oh-utils
uv run oh-conversation-manager
```

Test mode (simple list):
```bash
cd oh-utils
python3 conversation_manager/conversation_manager.py --test
```

Traditional method:
```bash
python3 conversation_manager/conversation_manager.py
```

**Interactive Commands:**
- `r`, `refresh` - Refresh conversation list
- `w <num>` - Wake up conversation by number (e.g., `w 3`)
- `s <num>` - Show detailed info for conversation (e.g., `s 1`)
- `n`, `next` - Next page
- `p`, `prev` - Previous page
- `h`, `help` - Show help
- `q`, `quit` - Exit

See the [Conversation Manager README](./conversation_manager/README.md) for detailed usage instructions.

## Requirements

- Python 3.8+
- requests >= 2.25.0

## API Access

These utilities require an OpenHands API token from:
https://app.all-hands.dev/settings/api-keys

## Contributing

Contributions welcome! Feel free to:
- Add new utilities
- Improve existing tools
- Report issues
- Suggest features

Each utility should be placed in its own subdirectory with appropriate documentation.

## License

MIT

This project is open source. Please check individual utility directories for specific license information.

## Links

- [OpenHands](https://www.all-hands.dev/)
- [OpenHands Documentation](https://docs.openhands.dev/)
- [API Documentation](https://docs.openhands.dev/api-reference)
