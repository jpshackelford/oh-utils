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
uv run oh-conversation-downloader
```

### Using pip

```bash
pip install -e .
```

## Utilities

### OpenHands API Utility / Conversation Downloader

A Python utility for downloading conversations and workspace files from the OpenHands Cloud API.

**Features:**
- Secure API key management
- List all conversations with pagination
- Download workspace archives
- Download changed files from conversations
- Interactive command-line interface
- Secure token storage
- Rate limit handling

**Quick Start:**

Using uv (recommended):
```bash
# Run directly from the project directory
cd oh-utils
uv run oh-conversation-downloader
```

Or after installation:
```bash
oh-conversation-downloader  # If installed in your PATH
```

Traditional method:
```bash
python3 openhands_api_utility/openhands_utility.py
```

See the [OpenHands API Utility README](./openhands_api_utility/README.md) for detailed usage instructions.

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
