# OpenHands Utilities

A collection of utilities for working with OpenHands (formerly All-Hands-AI / OpenDevin) API and conversations.

## Utilities

### [Conversation Downloader](./conversation-downloader/)

A Python utility for downloading conversations and workspace files from the OpenHands Cloud API.

**Features:**
- List all conversations with pagination
- Download workspace files to ZIP archives
- Two modes: full workspace or changed files only
- Interactive CLI interface
- Secure token storage
- Rate limit handling

**Quick Start:**
```bash
cd conversation-downloader
pip install -r requirements.txt
./openhands_conversation_downloader.py
```

### [OpenHands API Utility](./openhands-api-utility/)

A Python utility for managing OpenHands conversations via the API (if present).

**Features:**
- Secure API key management
- List and browse conversations with pagination
- Download workspace archives
- Download changed files from conversations
- Interactive command-line interface

See the specific utility directory for detailed usage instructions.

## Installation

```bash
git clone https://github.com/jpshackelford/oh-utils.git
cd oh-utils
```

Each utility has its own directory with specific requirements and documentation.

## Requirements

- Python 3.7+
- requests >= 2.31.0

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
