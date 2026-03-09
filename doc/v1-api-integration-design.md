# V1 API Integration for OpenHands Utilities

## 1. Introduction

### 1.1 Problem Statement

The oh-utils project currently supports only V0 OpenHands API endpoints, which limits functionality and prevents users from accessing the enhanced capabilities available in V1 conversations. V1 introduces a **two-tier API architecture** that separates conversation management from runtime operations. However, our current V1 API client implementation is incomplete, with most methods throwing `NotImplementedError`, and lacks proper integration with this two-tier architecture.

The key challenges are:

1. V1 uses a **two-tier API architecture**: App Server (conversations/sandboxes) and Agent Server (runtime operations)
2. Runtime operations require fetching sandbox info first to obtain the Agent Server URL and session key
3. Conversations and sandboxes are now **decoupled** - sandboxes are independent resources
4. Conversation creation is **asynchronous** in V1 (returns start task, not immediate conversation ID)
5. Missing implementation for core operations like file access, git changes, and trajectory
6. No workspace ZIP download capability in V1 (confirmed API gap)

### 1.2 V1 API Architecture Overview

V1 introduces two levels of API with different purposes and authentication:

| API | Base URL | Authentication | Purpose |
|-----|----------|----------------|---------|
| **App Server** | `app.all-hands.dev/api/v1/...` | `Authorization: Bearer {api_key}` | Manage conversations & sandboxes |
| **Agent Server** | `{sandbox_url}/api/...` | `X-Session-API-Key: {session_api_key}` | Runtime/workspace operations |

**Key architectural changes from V0:**

- **Decoupled resources**: Conversations and sandboxes are separate entities
- **Sandbox lifecycle**: Sandboxes can be paused/resumed independently
- **Agent Server per sandbox**: Each running sandbox has its own Agent Server URL
- **Session-based auth for runtime**: Agent Server uses `session_api_key` from sandbox info

### 1.3 Proposed Solution

We propose a focused V1 API integration that implements the core functionality needed for existing oh-utils commands to work with V1 conversations. The solution will:

1. **Implement two-tier API support**: Handle both App Server and Agent Server calls with appropriate authentication
2. **Add sandbox info retrieval**: Fetch sandbox details to obtain Agent Server URL and session key
3. **Complete V1 API client implementation**: Replace `NotImplementedError` placeholders with working implementations
4. **Maintain backward compatibility**: Ensure existing oh-utils commands work seamlessly with V1 conversations
5. **Leave workspace ZIP unimplemented**: Keep `download_workspace_archive()` as `NotImplementedError` (confirmed V1 API gap)

The design prioritizes functional parity with V0 capabilities rather than leveraging V1's enhanced features, ensuring a stable foundation for future enhancements.

## 2. Command Support Matrix

The following table shows current and planned support for oh-utils commands across API versions:

| Command               | V0 Support | V1 Current | V1 After Implementation |
| --------------------- | ---------- | ---------- | ----------------------- |
| `list`                | ✅         | ✅         | ✅                      |
| `download-files`      | ✅         | ❌         | ✅                      |
| `download-workspace`  | ✅         | ❌         | ❌ (API gap)            |
| `show-trajectory`     | ✅         | ❌         | ✅                      |
| `show-git-changes`    | ✅         | ❌         | ✅                      |
| `create-conversation` | ✅         | ✅         | ✅                      |

**Key:**

- ✅ = Fully supported
- ❌ = Not supported
- ❌ (API gap) = Cannot be implemented due to missing V1 API endpoint

This design document focuses on closing the gaps marked as "V1 After Implementation" while leaving workspace download unimplemented until the V1 API provides equivalent functionality.

### 2.1 User Experience

Users will experience familiar command patterns with V1 conversations:

```bash
# List conversations shows V1 conversations with sandbox information
$ oh-conversation-manager list
ID       Title                                    Status    Runtime   Sandbox
71468a85 Investigate V1 runtime API server       PAUSED    dxtugal   5MRNMGg
befbbf34 Test V1 conversation functionality      RUNNING   dxtugal   3Yn2ncz

# Download files works the same as V0
$ oh-conversation-manager download-files 71468a85
🔍 Fetching list of changed files...
📄 Found 12 changed files
📁 Downloading files to: files-71468a85-20231203-092000/
✅ Downloaded: src/api.py (2.3 KB)
✅ Downloaded: tests/test_api.py (5.1 KB)
...

# Workspace download shows clear error message
$ oh-conversation-manager download-workspace 71468a85
❌ Error: Workspace download not supported for V1 conversations
   This feature requires V1 API enhancement
```

## 3. Existing Infrastructure Analysis

### 3.1 API Fixture Recording and Sanitization Infrastructure

The project already has a comprehensive fixture infrastructure that follows established patterns:

**✅ Existing Components:**

- `scripts/update_fixtures.py` - Master orchestration script (needs V1 integration)
- `scripts/v0/record_api_responses.py` - V0 API recorder (established pattern)
- `scripts/v0/sanitize_fixtures.py` - V0 fixture sanitizer (established pattern)
- `scripts/v1/record_api_responses.py` - V1 API recorder (exists but needs runtime endpoint support)
- `scripts/v1/sanitize_fixtures.py` - V1 fixture sanitizer (exists but needs runtime-specific patterns)
- `tests/vcr_config.py` - VCR configuration with sanitization (needs V1 patterns)

**🔧 Required Updates:**

1. **Master Script**: Update `scripts/update_fixtures.py` to import and orchestrate V1 modules
2. **V1 Runtime Recording**: Enhance V1 recorder to capture runtime API interactions from active conversations
3. **V1 Runtime Sanitization**: Add sanitization patterns for `sandbox_id`, `conversation_url`, session keys
4. **VCR Integration**: Extend VCR configuration for V1 data structures and runtime URLs

This design will **continue existing patterns** rather than creating new infrastructure, ensuring consistency with established workflows.

## 4. V1 API Architecture Details

### 4.1 Two-Tier API Overview

V1 uses a two-tier architecture where the **App Server** manages high-level resources and the **Agent Server** handles runtime operations:

```
┌─────────────────────────────────────────────────────────────────┐
│                         App Server                               │
│                   (app.all-hands.dev/api/v1)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Conversations  │  │    Sandboxes    │  │     Events      │  │
│  │    /app-conv    │  │   /sandboxes    │  │ /conversation/  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│         Auth: Authorization: Bearer {api_key}                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Get sandbox info
                              │ (session_api_key + exposed_urls)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Server                              │
│              ({sandbox_url} from exposed_urls.AGENT_SERVER)      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │    Files    │  │     Git     │  │    Bash     │  │  Tools  │ │
│  │ /api/file/  │  │  /api/git/  │  │ /api/bash/  │  │/api/... │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│         Auth: X-Session-API-Key: {session_api_key}               │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 App Server Endpoints

The App Server (`app.all-hands.dev/api/v1/`) manages conversations and sandboxes:

**Conversation Management:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/app-conversations` | POST | Create conversation (returns start task) |
| `/app-conversations/search` | GET | Search conversations |
| `/app-conversations?id={id}` | GET | Get conversation by ID |
| `/app-conversations/start-tasks?id={id}` | GET | Poll start task status |
| `/app-conversations/stream-start` | POST | Stream conversation creation |

**Sandbox Management:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sandboxes?id={id}` | GET | Get sandbox info (returns `session_api_key` and `exposed_urls`) |
| `/sandboxes/search` | GET | Search sandboxes |
| `/sandboxes/{id}/pause` | POST | Pause sandbox |
| `/sandboxes/{id}/resume` | POST | Resume sandbox |
| `/sandboxes/{id}` | DELETE | Delete sandbox |

**Events (App Server):**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/conversation/{id}/events/search` | GET | Search events (paginated) |
| `/conversation/{id}/events/count` | GET | Count events |

### 4.3 Agent Server Endpoints

The Agent Server runs on each sandbox and provides runtime operations. Access it via the URL from `sandbox.exposed_urls.AGENT_SERVER`.

**File Operations:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/file/download/{path}` | GET | Download file content |
| `/api/file/upload/{path}` | POST | Upload file |
| `/api/file/download-trajectory/{conversation_id}` | GET | Download trajectory |

**Git Operations:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/git/changes/{path}` | GET | Get git changes |
| `/api/git/diff/{path}` | GET | Get git diff |

**Bash Operations:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bash/execute_bash_command` | POST | Execute bash command (blocking) |

**Conversation Operations (Agent Server):**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations/{id}/events` | POST | Send user message |
| `/api/conversations/{id}/events/search` | GET | Search events |

### 4.4 Authentication

| API | Header | Value Source |
|-----|--------|--------------|
| **App Server** | `Authorization` | `Bearer {api_key}` from user settings |
| **Agent Server** | `X-Session-API-Key` | `{session_api_key}` from sandbox info |

### 4.5 Sandbox Lifecycle States

| Status | Description | Agent Server Available? |
|--------|-------------|------------------------|
| `STARTING` | Sandbox is initializing | No |
| `RUNNING` | Sandbox is active | Yes |
| `PAUSED` | Sandbox is suspended (no billing) | No |
| `ERROR` | Something went wrong | No |
| `MISSING` | Sandbox no longer exists | No |

### 4.6 Critical Flow: Runtime Operations

To perform runtime operations (files, git, trajectory), the client must:

1. **Get conversation** → Extract `sandbox_id`
2. **Get sandbox info** → Extract `session_api_key` and `exposed_urls.AGENT_SERVER`
3. **Make Agent Server call** → Use `X-Session-API-Key` header

```python
# Step 1: Get conversation to find sandbox_id
conv = api.get_conversation(conversation_id)
sandbox_id = conv["sandbox_id"]

# Step 2: Get sandbox info for Agent Server access
sandbox = api.get_sandbox_info(sandbox_id)
agent_server_url = sandbox["exposed_urls"]["AGENT_SERVER"]
session_api_key = sandbox["session_api_key"]

# Step 3: Make Agent Server call
headers = {"X-Session-API-Key": session_api_key}
response = requests.get(f"{agent_server_url}/api/git/changes/.", headers=headers)
```

## 5. Technical Design

### 5.1 V1 API Client Structure

The V1 API client needs to handle both App Server and Agent Server calls:

```python
class OpenHandsAPI:
    """V1 API client with two-tier architecture support."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url  # App Server URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    # App Server methods (use self.session with Authorization header)
    def get_conversation(self, conversation_id: str) -> Dict[str, Any]: ...
    def get_sandbox_info(self, sandbox_id: str) -> Dict[str, Any]: ...
    def search_conversations(self, ...) -> List[Dict[str, Any]]: ...

    # Agent Server methods (require sandbox info first)
    def get_file_content(self, conversation_id: str, file_path: str, ...) -> str: ...
    def get_conversation_changes(self, conversation_id: str, ...) -> List[Dict]: ...
    def get_trajectory(self, conversation_id: str, ...) -> List[Dict]: ...

    # Helper for Agent Server calls
    def _make_agent_server_request(
        self,
        agent_server_url: str,
        session_api_key: str,
        endpoint: str,
        method: str = "GET",
        **kwargs
    ) -> requests.Response:
        """Make authenticated request to Agent Server."""
        headers = {"X-Session-API-Key": session_api_key}
        url = urljoin(agent_server_url, endpoint)
        return requests.request(method, url, headers=headers, **kwargs)
```

### 5.2 Sandbox Info Retrieval

New method to get sandbox details including Agent Server access:

```python
def get_sandbox_info(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
    """
    Get sandbox information including Agent Server URL and session key.

    Args:
        sandbox_id: The sandbox ID from conversation data

    Returns:
        Sandbox info dict with keys:
        - id: Sandbox ID
        - status: STARTING, RUNNING, PAUSED, ERROR, MISSING
        - session_api_key: Key for Agent Server authentication
        - exposed_urls: Dict with AGENT_SERVER, VSCODE, etc.

    Raises:
        Exception: If sandbox not found or not running
    """
    url = urljoin(self.base_url, f"v1/sandboxes?id={sandbox_id}")
    response = self.session.get(url)
    response.raise_for_status()
    return response.json()
```

### 5.3 Core Methods Implementation

#### 5.3.1 get_conversation()

```python
def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation details from App Server."""
    url = urljoin(self.base_url, f"v1/app-conversations?id={conversation_id}")
    response = self.session.get(url)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()
```

#### 5.3.2 get_conversation_changes()

```python
def get_conversation_changes(
    self,
    conversation_id: str,
    runtime_url: Optional[str] = None,  # Agent Server URL if known
) -> Optional[List[Dict[str, str]]]:
    """Get git changes using Agent Server API."""
    # Get sandbox info if runtime_url not provided
    if not runtime_url:
        conv = self.get_conversation(conversation_id)
        if not conv or not conv.get("sandbox_id"):
            return None
        sandbox = self.get_sandbox_info(conv["sandbox_id"])
        if not sandbox or sandbox.get("status") != "RUNNING":
            raise Exception("Sandbox is not running - cannot access workspace")
        runtime_url = sandbox["exposed_urls"]["AGENT_SERVER"]
        session_key = sandbox["session_api_key"]
    else:
        # Assume session key passed separately or retrieved
        session_key = self._get_session_key_for_url(runtime_url)

    response = self._make_agent_server_request(
        runtime_url, session_key, "api/git/changes/."
    )
    response.raise_for_status()
    return response.json()
```

#### 5.3.3 get_file_content()

```python
def get_file_content(
    self,
    conversation_id: str,
    file_path: str,
    runtime_url: Optional[str] = None,
) -> Optional[str]:
    """Download file content from Agent Server."""
    # Get sandbox info for Agent Server access
    conv = self.get_conversation(conversation_id)
    if not conv or not conv.get("sandbox_id"):
        return None
    sandbox = self.get_sandbox_info(conv["sandbox_id"])
    if not sandbox or sandbox.get("status") != "RUNNING":
        raise Exception("Sandbox is not running - cannot access files")

    agent_url = sandbox["exposed_urls"]["AGENT_SERVER"]
    session_key = sandbox["session_api_key"]

    response = self._make_agent_server_request(
        agent_url, session_key, f"api/file/download/{file_path}"
    )
    response.raise_for_status()
    return response.text
```

#### 5.3.4 get_trajectory()

```python
def get_trajectory(
    self,
    conversation_id: str,
    runtime_url: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Download trajectory from Agent Server."""
    # Get sandbox info for Agent Server access
    conv = self.get_conversation(conversation_id)
    if not conv or not conv.get("sandbox_id"):
        return None
    sandbox = self.get_sandbox_info(conv["sandbox_id"])
    if not sandbox or sandbox.get("status") != "RUNNING":
        raise Exception("Sandbox is not running - cannot access trajectory")

    agent_url = sandbox["exposed_urls"]["AGENT_SERVER"]
    session_key = sandbox["session_api_key"]

    response = self._make_agent_server_request(
        agent_url, session_key, f"api/file/download-trajectory/{conversation_id}"
    )
    response.raise_for_status()
    return response.json()
```

### 5.4 Workspace Archive Gap

V1 does not provide a workspace ZIP download endpoint. This method will remain unimplemented:

```python
def download_workspace_archive(
    self, conversation_id: str, runtime_url: Optional[str] = None
) -> Optional[bytes]:
    """Download workspace archive (not supported in V1)."""
    raise NotImplementedError(
        "Workspace ZIP download is not supported for V1 conversations. "
        "This is a known V1 API gap. "
        "Use 'download-files' command to get individual changed files, "
        "or use the OpenHands Agent SDK workspace.get_workspace_zip() method."
    )
```

### 5.5 Existing API Fixture Infrastructure

The project already has a comprehensive fixture recording and sanitization infrastructure that follows established patterns:

#### 5.5.1 Master Fixture Update Script

`scripts/update_fixtures.py` provides a unified workflow for updating API fixtures:

- Orchestrates both recording and sanitization phases
- Supports both V0 and V1 API versions
- Provides command-line options for selective operations (record-only, sanitize-only)
- Currently imports from V0 modules but needs V1 integration

#### 5.5.2 Version-Specific Infrastructure

**V0 Infrastructure (Established Pattern):**

- `scripts/v0/record_api_responses.py` - `APIResponseRecorder` class for V0 endpoints
- `scripts/v0/sanitize_fixtures.py` - `FixtureSanitizer` class for V0 data patterns

**V1 Infrastructure (Existing but Incomplete):**

- `scripts/v1/record_api_responses.py` - `V1APIResponseRecorder` class (needs Agent Server endpoint support)
- `scripts/v1/sanitize_fixtures.py` - `V1FixtureSanitizer` class (needs Agent Server-specific patterns)

#### 5.5.3 VCR Integration

`tests/vcr_config.py` provides VCR configuration for HTTP interaction recording:

- Sanitizes sensitive headers (`X-Session-API-Key`, `Authorization`)
- Filters sensitive request/response data
- Uses YAML serialization for readability
- Needs V1-specific sanitization patterns for Agent Server URLs and session keys

#### 5.5.4 Required Updates for V1 Support

1. **Master Script Integration**: Update `scripts/update_fixtures.py` to import and use V1 modules
2. **Agent Server Endpoint Recording**: Enhance V1 recorder to capture Agent Server API interactions
3. **V1-Specific Sanitization**: Add patterns for `sandbox_id`, `exposed_urls`, Agent Server hostnames
4. **VCR Configuration**: Extend sanitization for V1 data structures and Agent Server URLs

## 6. Implementation Plan

All implementations must pass existing lints and tests. New functionality requires comprehensive test coverage with both unit tests and integration tests using VCR fixtures.

### 6.1 V1 API Client Core Implementation (M1)

Complete the V1 API client with working implementations for all placeholder methods.

#### 6.1.1 Sandbox Info Retrieval

- `ohc/v1/api.py` - Add `get_sandbox_info()` method to fetch Agent Server URL and session key
- `tests/test_v1_api_sandbox.py` - Test sandbox info retrieval

#### 6.1.2 App Server Methods

- `ohc/v1/api.py` - Implement `get_conversation()` using `GET /v1/app-conversations?id={id}`
- `tests/test_v1_api_conversation.py` - Test conversation retrieval

#### 6.1.3 Agent Server File Operations

- `ohc/v1/api.py` - Add `_make_agent_server_request()` helper for authenticated Agent Server calls
- `ohc/v1/api.py` - Implement `get_file_content()` using Agent Server `/api/file/download/{path}`
- `ohc/v1/api.py` - Implement `get_conversation_changes()` using Agent Server `/api/git/changes/.`
- `tests/test_v1_api_files.py` - Test file operations with VCR fixtures

#### 6.1.4 Agent Server Trajectory Operations

- `ohc/v1/api.py` - Implement `get_trajectory()` using Agent Server `/api/file/download-trajectory/{id}`
- `tests/test_v1_api_trajectory.py` - Test trajectory download

#### 6.1.5 API Fixture Recording Infrastructure

- `scripts/update_fixtures.py` - Update master script to support V1 alongside existing V0 support
- `scripts/v1/record_api_responses.py` - Enhance existing V1 recorder with Agent Server endpoint recording
- `scripts/v1/sanitize_fixtures.py` - Update existing V1 sanitizer with Agent Server-specific sanitization patterns

**Demo**: Basic V1 file operations work - can download files and get git changes from active V1 conversations via Agent Server. API fixture infrastructure supports V1 endpoint recording and sanitization.

### 6.2 V1 Conversation Management Integration (M2)

Integrate V1 API client with existing conversation manager workflows.

#### 6.2.1 Conversation Manager V1 Support

- `conversation_manager/conversation_manager.py` - Update to use two-tier API architecture
- `conversation_manager/conversation_manager.py` - Handle sandbox info retrieval for Agent Server access
- `tests/test_conversation_manager_v1.py` - Test V1 conversation management

#### 6.2.2 Command Integration

- `ohc/conversation_commands.py` - Update all commands to work with V1 conversations via Agent Server
- `ohc/conversation_display.py` - Update display formatting for V1 conversation/sandbox data
- `tests/test_v1_command_integration.py` - Test all commands work with V1 conversations

#### 6.2.3 VCR Configuration Updates

- `tests/vcr_config.py` - Extend existing VCR configuration with V1-specific sanitization patterns
- Update existing `sanitize_request()` and `sanitize_response()` functions for V1 data structures

**Demo**: All existing oh-utils commands work seamlessly with V1 conversations. VCR-based integration tests properly sanitize V1 API interactions.

### 6.3 Enhanced Error Handling and User Experience (M3)

Improve error handling and user experience for V1 conversations.

#### 6.3.1 Inactive Sandbox Handling

- `ohc/v1/api.py` - Add clear error messages when sandbox is not running (PAUSED, ERROR, MISSING)
- `ohc/conversation_commands.py` - Add sandbox activation guidance (resume commands)
- `tests/test_v1_inactive_sandbox.py` - Test inactive sandbox scenarios

#### 6.3.2 Enhanced Status Display

- `ohc/conversation_display.py` - Add sandbox status and Agent Server availability to displays
- `conversation_manager/conversation_manager.py` - Show V1-specific status information (sandbox state)
- `tests/test_v1_display.py` - Test enhanced display formatting

**Demo**: Users receive clear feedback about sandbox states and guidance for resuming paused sandboxes.

### 6.4 Comprehensive Testing and Documentation (M4)

Ensure robust testing coverage and complete documentation.

#### 6.4.1 API Fixture Infrastructure Updates

- `scripts/update_fixtures.py` - Update master script to import and orchestrate V1 modules alongside V0
- `scripts/v1/record_api_responses.py` - Enhance existing V1 recorder with Agent Server endpoint support:
  - Add sandbox info retrieval to discover Agent Server URL
  - Record Agent Server `/api/file/download/{path}` endpoints
  - Record Agent Server `/api/git/changes/.` endpoints
  - Record Agent Server `/api/file/download-trajectory/{id}` endpoints
  - Handle session-based authentication with `X-Session-API-Key` headers
- `scripts/v1/sanitize_fixtures.py` - Enhance existing V1 sanitizer with V1-specific patterns:
  - Add `sandbox_id` sanitization patterns
  - Add `exposed_urls.AGENT_SERVER` sanitization for Agent Server hostnames
  - Add session API key sanitization patterns
  - Maintain consistency with V0 sanitization approach
- `tests/vcr_config.py` - Extend VCR configuration for V1 data structures:
  - Add V1 conversation/sandbox data sanitization
  - Add Agent Server URL sanitization patterns
  - Add session key filtering for Agent Server authentication

#### 6.4.2 Integration Test Suite

- `tests/test_v1_integration.py` - Comprehensive integration tests covering all V1 workflows
- `tests/fixtures/v1/` - Complete VCR fixture set for all V1 API interactions using updated recording infrastructure

#### 6.4.3 Documentation Updates

- `README.md` - Update with V1 capabilities and usage examples
- `doc/v1-api-migration-guide.md` - Migration guide for V0 to V1 workflows

**Demo**: Complete V1 API integration with comprehensive test coverage and documentation, ready for production use.

## Appendix: Future Enhancement Opportunities

The V1 Agent Server API provides significantly more capabilities than V0. While this design focuses on functional parity, the following enhancements could be considered for future development:

### A.1 Enhanced V1 Capabilities

#### A.1.1 Bash Command Execution

- `ohc/v1/api.py` - Add `execute_bash_command()` method using Agent Server `/api/bash/execute_bash_command`
- `ohc/conversation_commands.py` - Add `exec` command for direct bash execution
- `tests/test_v1_bash_execution.py` - Test bash command execution

#### A.1.2 Development Environment Access

- `ohc/v1/api.py` - Add `get_vscode_url()` using `sandbox.exposed_urls.VSCODE`
- `ohc/v1/api.py` - Add `get_desktop_url()` using Agent Server `/api/desktop/url`
- `ohc/conversation_commands.py` - Add `vscode` and `desktop` commands
- `tests/test_v1_dev_environment.py` - Test development environment access

#### A.1.3 Event Management

- `ohc/v1/api.py` - Add event search methods using App Server `/v1/conversation/{id}/events/search`
- `ohc/conversation_commands.py` - Add event browsing and filtering commands
- `tests/test_v1_events.py` - Test event management functionality

#### A.1.4 Tool Integration

- `ohc/v1/api.py` - Add tool listing using Agent Server `/api/tools/`
- `ohc/conversation_commands.py` - Add tool discovery commands
- `tests/test_v1_tools.py` - Test tool integration

#### A.1.5 Sandbox Management

- `ohc/v1/api.py` - Add `pause_sandbox()`, `resume_sandbox()`, `delete_sandbox()` methods
- `ohc/conversation_commands.py` - Add sandbox management commands
- `tests/test_v1_sandbox_management.py` - Test sandbox lifecycle management

These enhancements would leverage V1's rich API to provide capabilities not available in V0, such as direct bash execution, development environment access, comprehensive event tracking, and explicit sandbox lifecycle control.
