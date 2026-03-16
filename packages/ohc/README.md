# ohc - OpenHands Cloud CLI

Administrative command-line tools for managing OpenHands Cloud and Enterprise deployments.

## Overview

`ohc` is a CLI tool for administrators and developers who need to manage OpenHands deployments, conversations, and debug issues. It provides server configuration, conversation management, and debugging capabilities.

**Note**: This is an administrative tool. For end-user agent interactions, see the main OpenHands CLI which wraps the Agent SDK.

## Installation

```bash
pip install ohc
```

This will also install `ohc-lib` as a dependency.

## Quick Start

### Configure a Server

```bash
# Add OpenHands Cloud
ohc server add cloud https://app.all-hands.dev/api/ YOUR_API_KEY --default

# Add an Enterprise deployment
ohc server add enterprise https://your-company.openhands.dev/api/ YOUR_API_KEY
```

### List Conversations

```bash
# List all conversations
ohc conv list

# List last 10 conversations
ohc conv list -n 10
```

### View Conversation Details

```bash
# By number (from list)
ohc conv show 1

# By partial ID
ohc conv show abc123

# By full ID
ohc conv show 12345678-1234-1234-1234-123456789abc
```

### Interactive Mode

```bash
ohc -i
```

## Commands

### Server Management

```bash
ohc server add <name> <url> <api-key> [--default]
ohc server list
ohc server remove <name>
ohc server default <name>
```

### Conversation Management

```bash
ohc conv list [-n NUMBER]
ohc conv show <id-or-number>
ohc conv changes <id-or-number>
ohc conv download <id-or-number> [--output PATH]
```

### Debugging (Enterprise)

```bash
ohc debug health
ohc debug list
ohc debug runtime <conversation-id>
```

## API Version Selection

```bash
# Use v0 API (legacy)
ohc --api-version v0 conv list

# Use v1 API (recommended)
ohc --api-version v1 conv list
```

## Configuration

Configuration is stored at `~/.config/ohc/config.json` following the XDG Base Directory Specification.

## Related Packages

- **ohc-lib**: The underlying Python library for programmatic API access

## License

MIT License - see LICENSE file for details.
