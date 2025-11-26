# OpenHands API Reference

This document provides a comprehensive reference for the OpenHands API endpoints used by the oh-utils project. All examples are based on actual API responses captured in the test fixtures and production code usage.

## Base Configuration

**Base URL**: `https://app.all-hands.dev/api/`  
**Authentication**: `X-Session-API-Key` header  
**Content-Type**: `application/json`

## API Endpoints

### 1. Test Connection

**Endpoint**: `GET /options/models`  
**Purpose**: Test API key validity and connection  
**Authentication**: Required

#### Request
```http
GET https://app.all-hands.dev/api/options/models
Headers:
  X-Session-API-Key: <your-api-key>
  Content-Type: application/json
```

#### Response
```http
Status: 200 OK
Content-Type: application/json

[
  "1024-x-1024/50-steps/bedrock/amazon.nova-canvas-v1:0",
  "1024-x-1024/50-steps/stability.stable-diffusion-xl-v1",
  "1024-x-1024/dall-e-2",
  "azure/gpt-4o",
  "claude-3-5-sonnet-20241022",
  "gpt-4o",
  "gpt-4o-mini",
  ...
]
```

**Usage**: Returns a large array of available model names. A 200 status indicates valid API key.

---

### 2. List Conversations

**Endpoint**: `GET /conversations`  
**Purpose**: Retrieve paginated list of conversations  
**Authentication**: Required

#### Request
```http
GET https://app.all-hands.dev/api/conversations?limit=5
Headers:
  X-Session-API-Key: <your-api-key>
  Content-Type: application/json
```

#### Parameters
- `limit` (optional): Number of conversations to return (default: 20)
- `page_id` (optional): Pagination token for next page

#### Response
```http
Status: 200 OK
Content-Type: application/json

{
  "results": [
    {
      "conversation_id": "d2bfa2e22a0e4fef98882ab95258d4af",
      "title": "Test Release Process Before Merging to Main",
      "last_updated_at": "2024-01-15T10:30:00.000Z.489661Z",
      "status": "RUNNING",
      "runtime_status": "STATUS$READY",
      "selected_repository": "jpshackelford/oh-utils",
      "selected_branch": "jps/ci",
      "git_provider": "github",
      "trigger": "resolver",
      "num_connections": 0,
      "url": "https://fakeworkspace006.prod-runtime.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af",
      "session_api_key": "6510f16e-d319-4c78-9257-e3cd9da8e12c",
      "created_at": "2024-01-15T10:30:00.000Z.842270Z",
      "pr_number": [],
      "conversation_version": "V0"
    }
  ],
  "next_page_id": "eyJ2MCI6ICJNUT09IiwgInYxIjogbnVsbH0="
}
```

#### Response Fields
- `results`: Array of conversation objects
- `next_page_id`: Token for pagination (null if no more pages)

#### Conversation Object Fields
- `conversation_id`: Unique identifier for the conversation
- `title`: Human-readable conversation title
- `status`: Current status (`RUNNING`, `STOPPED`, etc.)
- `runtime_status`: Runtime-specific status (`STATUS$READY`, etc.)
- `url`: Runtime URL for active conversations (null for stopped)
- `session_api_key`: Session-specific API key for runtime operations
- `selected_repository`: Associated GitHub repository
- `selected_branch`: Git branch being worked on
- `git_provider`: Version control provider (`github`)
- `trigger`: How conversation was started (`gui`, `resolver`)

---

### 3. Get Conversation Details

**Endpoint**: `GET /conversations/{conversation_id}`  
**Purpose**: Get detailed information about a specific conversation  
**Authentication**: Required

#### Request
```http
GET https://app.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af
Headers:
  X-Session-API-Key: <your-api-key>
  Content-Type: application/json
```

#### Response
```http
Status: 200 OK
Content-Type: application/json

{
  "conversation_id": "d2bfa2e22a0e4fef98882ab95258d4af",
  "title": "Example Conversation",
  "last_updated_at": "2024-01-15T10:30:00.000Z.489661Z",
  "status": "RUNNING",
  "runtime_status": "STATUS$READY",
  "selected_repository": "jpshackelford/oh-utils",
  "selected_branch": "jps/ci",
  "git_provider": "github",
  "trigger": "resolver",
  "num_connections": 0,
  "url": "https://fakeworkspace006.prod-runtime.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af",
  "session_api_key": "6510f16e-d319-4c78-9257-e3cd9da8e12c",
  "created_at": "2024-01-15T10:30:00.000Z.842270Z",
  "pr_number": [],
  "conversation_version": "V0"
}
```

**Error Response** (404):
```http
Status: 404 Not Found
Content-Type: application/json

{
  "error": "Conversation not found"
}
```

---

### 4. Start/Wake Conversation

**Endpoint**: `POST /conversations/{conversation_id}/start`  
**Purpose**: Start or wake up a conversation  
**Authentication**: Required

#### Request
```http
POST https://app.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af/start
Headers:
  X-Session-API-Key: <your-api-key>
  Content-Type: application/json

{
  "providers_set": ["github"]
}
```

#### Request Body
- `providers_set`: Array of provider names (default: `["github"]`)

#### Response
```http
Status: 200 OK
Content-Type: application/json

{
  "status": "ok",
  "conversation_id": "d2bfa2e22a0e4fef98882ab95258d4af",
  "message": null,
  "conversation_status": "RUNNING"
}
```

---

## Runtime API Endpoints

These endpoints are called on the runtime URL (extracted from conversation details) rather than the main API base URL.

### 5. Get Git Changes

**Endpoint**: `GET {runtime_url}/api/conversations/{conversation_id}/git/changes`  
**Purpose**: Get uncommitted git changes in the workspace  
**Authentication**: Session API key required

#### Request
```http
GET https://fakeworkspace112.prod-runtime.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af/git/changes
Headers:
  X-Session-API-Key: 6510f16e-d319-4c78-9257-e3cd9da8e12c
  Content-Type: application/json
```

#### Response (No Changes)
```http
Status: 200 OK
Content-Type: application/json

[]
```

#### Response (With Changes)
```http
Status: 200 OK
Content-Type: application/json

[
  {
    "file": "src/main.py",
    "status": "modified"
  },
  {
    "file": "README.md",
    "status": "added"
  }
]
```

#### Error Responses
- `404`: No git repository or no changes
- `500`: Git repository not available or corrupted

---

### 6. Get File Content

**Endpoint**: `GET {runtime_url}/api/conversations/{conversation_id}/select-file`  
**Purpose**: Retrieve content of a specific file from the workspace  
**Authentication**: Session API key required

#### Request
```http
GET https://fakeworkspace114.prod-runtime.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af/select-file?file=README.md
Headers:
  X-Session-API-Key: 6510f16e-d319-4c78-9257-e3cd9da8e12c
  Content-Type: application/json
```

#### Parameters
- `file`: Path to the file to retrieve

#### Response (Success)
```http
Status: 200 OK
Content-Type: application/json

{
  "code": "# Project Title\n\nThis is the content of the README file..."
}
```

#### Error Response (File Not Found)
```http
Status: 500 Internal Server Error
Content-Type: application/json

{
  "error": "Error opening file: **ErrorObservation**\nFile not found: /workspace/project/README.md. Your current working directory is /workspace/project/oh-utils."
}
```

---

### 7. Download Workspace Archive

**Endpoint**: `GET {runtime_url}/api/conversations/{conversation_id}/zip-directory`  
**Purpose**: Download the entire workspace as a ZIP file  
**Authentication**: Session API key required

#### Request
```http
GET https://fakeworkspace006.prod-runtime.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af/zip-directory
Headers:
  X-Session-API-Key: 6510f16e-d319-4c78-9257-e3cd9da8e12c
```

#### Response
```http
Status: 200 OK
Content-Type: application/zip
Content-Length: <size>

<binary ZIP data>
```

#### Error Responses
- `404`: Workspace not found for conversation
- `401`: Authentication failed - invalid session API key
- `500`: Server error - workspace may be inaccessible

---

### 8. Get Trajectory

**Endpoint**: `GET {runtime_url}/api/conversations/{conversation_id}/trajectory`  
**Purpose**: Get conversation trajectory data (action history)  
**Authentication**: Session API key required

#### Request
```http
GET https://fakeworkspace014.prod-runtime.all-hands.dev/api/conversations/d2bfa2e22a0e4fef98882ab95258d4af/trajectory
Headers:
  X-Session-API-Key: 6510f16e-d319-4c78-9257-e3cd9da8e12c
  Content-Type: application/json
```

#### Response
```http
Status: 200 OK
Content-Type: application/json

{
  "trajectory": [
    {
      "id": 0,
      "timestamp": "2024-01-15T10:30:00.000Z.362035",
      "source": "environment",
      "message": "",
      "observation": "agent_state_changed",
      "content": "",
      "extras": {
        "agent_state": "loading",
        "reason": ""
      }
    },
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00.000Z.317663",
      "source": "agent",
      "message": "System prompt content...",
      "action": "system",
      "args": {
        "content": "System initialization message..."
      }
    }
  ]
}
```

#### Trajectory Entry Fields
- `id`: Sequential identifier for the trajectory entry
- `timestamp`: ISO timestamp of the action
- `source`: Source of the action (`agent`, `environment`, `user`)
- `message`: Human-readable message
- `observation`: Type of observation (for environment entries)
- `action`: Action type (for agent entries)
- `args`: Action arguments
- `extras`: Additional metadata

---

## Error Handling

### Common HTTP Status Codes
- `200`: Success
- `401`: Unauthorized - Invalid or missing API key
- `404`: Not Found - Resource doesn't exist
- `500`: Internal Server Error - Server-side issue

### Authentication Errors
When using an invalid API key:
```http
Status: 401 Unauthorized

{
  "error": "API key does not have permission to access conversations. Please ensure you're using a full API key from your OpenHands settings."
}
```

## Usage Notes

1. **API Key Types**: Ensure you're using a full API key from OpenHands settings, not a limited key.

2. **Runtime URLs**: For active conversations, use the `url` field from conversation details as the base URL for runtime operations.

3. **Session API Keys**: Runtime operations require the `session_api_key` from conversation details.

4. **Pagination**: Use `next_page_id` from list responses to fetch additional pages.

5. **File Paths**: File paths in `select-file` requests are relative to the workspace root.

6. **Git Operations**: Git-related endpoints may return 404 or 500 if the workspace doesn't have a git repository or if there are git-related issues.

## Code Examples

### Python Usage (from oh-utils codebase)

```python
import requests
from urllib.parse import urljoin

class OpenHandsAPI:
    def __init__(self, api_key: str, base_url: str = "https://app.all-hands.dev/api/"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Session-API-Key": api_key,
            "Content-Type": "application/json"
        })
    
    def search_conversations(self, page_id=None, limit=20):
        url = urljoin(self.base_url, "conversations")
        params = {"limit": limit}
        if page_id:
            params["page_id"] = page_id
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def start_conversation(self, conversation_id, providers_set=None):
        url = urljoin(self.base_url, f"conversations/{conversation_id}/start")
        data = {"providers_set": providers_set or ["github"]}
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
```

This reference is based on the actual API usage patterns found in the oh-utils codebase and the sanitized fixture data from the test suite.