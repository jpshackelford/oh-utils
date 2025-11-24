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
uv run oh-conversation-manager
```

### Using pip

```bash
pip install -e .
```

## Utilities

This repository contains a comprehensive utility for working with OpenHands conversations:

### Conversation Manager

**Command:** `uv run oh-conversation-manager`

A terminal-based interactive utility for managing OpenHands conversations.

**Features:**
- 🔐 Secure API key management
- 📋 List conversations with status, runtime IDs, and titles
- 🖥️ Terminal-aware formatting that adapts to screen size
- 📄 Pagination for handling large numbers of conversations
- 🔄 Real-time refresh to see updated conversation states
- ⚡ Wake up conversations by number to start inactive ones
- 🔍 Detailed conversation info with full metadata
- 📦 Download workspace archives
- 📄 Download changed files from conversations
- 🎯 Interactive commands for easy navigation and management
- 💬 Comprehensive conversation management interface

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
- `d <num>` - Download changed files for conversation (e.g., `d 1`)
- `t <num>` - Download trajectory data for conversation (e.g., `t 1`)
- `a <num>` - Download full workspace archive for conversation (e.g., `a 1`)
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
