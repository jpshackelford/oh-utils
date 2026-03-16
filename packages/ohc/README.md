# ohc

OpenHands Cloud API Client Library - Programmatic access to OpenHands Cloud and Agent Server REST APIs.

## Overview

`ohc` is a Python library for administrators and developers who need programmatic access to OpenHands Cloud and Enterprise deployments. It provides a clean, well-typed interface to both the v0 and v1 REST APIs.

**Note**: This library is for administrative and automation use cases. For end-user agent interactions, see the main OpenHands CLI which wraps the Agent SDK.

## Installation

```bash
pip install ohc
```

## Quick Start

```python
from ohc import OpenHandsAPI

# Create a client (defaults to v0 API)
api = OpenHandsAPI(
    api_key="your-api-key",
    base_url="https://app.all-hands.dev/api/",
    version="v1"  # or "v0"
)

# Test connection
if api.test_connection():
    print("Connected successfully!")

# List conversations
result = api.search_conversations(limit=10)
for conv in result["results"]:
    print(f"{conv['conversation_id']}: {conv.get('title', 'Untitled')}")

# Get conversation details
details = api.get_conversation("your-conversation-id")
print(f"Status: {details.get('status')}")
```

## API Versions

### V0 API (Legacy)
The original OpenHands API with simpler endpoints. Use for basic conversation management.

```python
from ohc.v0 import OpenHandsAPI

api = OpenHandsAPI(api_key="your-key")
conversations = api.search_conversations()
```

### V1 API (Recommended)
The newer two-tier architecture with App Server and Agent Server separation. Provides enhanced functionality including event search and better sandbox management.

```python
from ohc.v1 import OpenHandsAPI, SandboxNotRunningError

api = OpenHandsAPI(api_key="your-key")

# Search events
events = api.search_events(conversation_id="conv-id", limit=50)

# Handle sandbox state
try:
    changes = api.get_conversation_changes("conv-id")
except SandboxNotRunningError as e:
    print(f"Sandbox {e.sandbox_id} is {e.status}")
```

## Core Features

- **Conversation Management**: List, search, create, and manage conversations
- **Workspace Operations**: Download workspace archives, get file contents, view git changes
- **Event Search** (v1): Search and filter events across conversations
- **Trajectory Access**: Retrieve conversation trajectories for analysis
- **Sandbox Management** (v1): Start sandboxes, check status, interact with runtime

## Authentication

Get your API key from:
- **Cloud**: https://app.all-hands.dev/settings/api-keys
- **Enterprise**: Your organization's OpenHands deployment settings

## Error Handling

```python
from ohc import OpenHandsAPI
from ohc.v1 import SandboxNotRunningError
import requests

api = OpenHandsAPI(api_key="your-key", version="v1")

try:
    changes = api.get_conversation_changes("conv-id")
except SandboxNotRunningError as e:
    # Sandbox needs to be started
    api.start_conversation(e.sandbox_id)
except requests.HTTPError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
    elif e.response.status_code == 404:
        print("Conversation not found")
```

## License

MIT License - see LICENSE file for details.
