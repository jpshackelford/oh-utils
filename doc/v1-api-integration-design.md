# V1 API Integration for OpenHands Utilities

## 1. Introduction

### 1.1 Problem Statement

The oh-utils project currently supports only V0 OpenHands API endpoints, which limits functionality and prevents users from accessing the enhanced capabilities available in V1 conversations. V1 conversations provide a significantly richer runtime API with comprehensive event management, file operations, bash command execution, and development environment integration. However, our current V1 API client implementation is incomplete, with most methods throwing `NotImplementedError`, and lacks proper integration with the V1 runtime agent server APIs.

The key challenges are:

1. V1 conversations use a different data structure (`sandbox_id` instead of direct `url` field)
2. Runtime URL discovery requires understanding the V1 conversation lifecycle
3. V1 runtime APIs offer much more functionality than we currently utilize
4. Missing implementation for core operations like workspace downloads, file access, and git changes
5. No workspace ZIP download capability in V1 (significant gap)

### 1.2 Proposed Solution

We propose a focused V1 API integration that implements the core functionality needed for existing oh-utils commands to work with V1 conversations. The solution will:

1. **Implement proper V1 conversation discovery**: Use `/api/v1/app-conversations/search` to list conversations and extract runtime URLs from active conversations
2. **Complete V1 API client implementation**: Replace `NotImplementedError` placeholders with working implementations using V1 runtime endpoints for core operations (file access, git changes, trajectory)
3. **Maintain backward compatibility**: Ensure existing oh-utils commands work seamlessly with V1 conversations
4. **Leave workspace ZIP unimplemented**: Keep `download_workspace_archive()` as `NotImplementedError` until V1 API provides equivalent functionality

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

## 4. Other Context

### 4.1 V1 Runtime Agent Server Architecture

V1 conversations run on a sophisticated runtime agent server that provides a comprehensive REST API. The server is built with FastAPI and includes:

- **Event System**: Complete event tracking and management
- **File Operations**: Upload/download with path-based access
- **Bash Integration**: Direct command execution and event logging
- **Development Tools**: VSCode and desktop environment access
- **Git Operations**: Enhanced git change tracking and diff capabilities
- **Tool Management**: Access to available AI tools and capabilities

### 4.2 Authentication and Session Management

V1 runtime APIs use session-based authentication where active conversations provide a `session_api_key` that must be included in runtime API calls via the `X-Session-API-Key` header.

### 4.3 Conversation Lifecycle

V1 conversations have distinct states:

- **PAUSED**: Conversation exists but runtime is not active (`conversation_url` is null)
- **RUNNING**: Conversation is active with runtime server (`conversation_url` points to runtime)
- **STOPPED**: Conversation is terminated

## 5. Technical Design

### 6.1 V1 Conversation Discovery and Runtime URL Extraction

#### 6.1.1 Conversation Data Structure

V1 conversations returned by `/api/v1/app-conversations/search` have this structure:

```json
{
  "id": "71468a85bc394784a2e06e3c61f7774c",
  "sandbox_id": "5MRNMGgpxliEirAhrCeqjY",
  "conversation_url": "https://dxtugalgwuthebpf.prod-runtime.all-hands.dev/api/conversations/71468a85bc394784a2e06e3c61f7774c",
  "session_api_key": "session-key-here",
  "sandbox_status": "RUNNING",
  "title": "My V1 Conversation"
}
```

#### 6.1.2 Runtime URL Extraction Logic

```python
def extract_runtime_url(conversation: Dict[str, Any]) -> Optional[str]:
    """Extract runtime base URL from V1 conversation data."""
    conversation_url = conversation.get("conversation_url")
    if not conversation_url:
        return None

    from urllib.parse import urlparse
    parsed = urlparse(conversation_url)
    return f"{parsed.scheme}://{parsed.netloc}"
```

### 6.2 V1 API Client Implementation

#### 6.2.1 Core Methods Implementation

Replace `NotImplementedError` methods with working implementations:

```python
def get_conversation_changes(
    self, conversation_id: str, runtime_url: str, session_api_key: str
) -> List[Dict[str, str]]:
    """Get git changes using V1 runtime API."""
    url = urljoin(runtime_url, f"api/git/changes/.")
    headers = {"X-Session-API-Key": session_api_key}

    response = self.session.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_file_content(
    self, conversation_id: str, file_path: str, runtime_url: str, session_api_key: str
) -> str:
    """Download file content using V1 runtime API."""
    url = urljoin(runtime_url, f"api/file/download/{file_path}")
    headers = {"X-Session-API-Key": session_api_key}

    response = self.session.get(url, headers=headers)
    response.raise_for_status()
    return response.text
```

### 6.3 Workspace Archive Gap

V1 runtime API does not provide a direct workspace ZIP endpoint equivalent to V0's `/zip-directory`. The `download_workspace_archive()` method will remain as `NotImplementedError` with a clear error message directing users to use individual file downloads until this API gap is addressed.

```python
def download_workspace_archive(
    self, conversation_id: str, runtime_url: Optional[str] = None
) -> Optional[bytes]:
    """Download workspace archive (not supported in V1)."""
    raise NotImplementedError(
        "Workspace download not supported for V1 conversations. "
        "This feature requires V1 API enhancement. "
        "Use download-files command to get individual files."
    )
```

### 6.4 Enhanced Conversation Management

#### 6.4.1 V1 Conversation Class

```python
@dataclass
class V1Conversation:
    """Enhanced conversation class for V1 API."""
    id: str
    title: str
    sandbox_id: str
    sandbox_status: str
    conversation_url: Optional[str]
    session_api_key: Optional[str]
    created_at: str
    updated_at: str

    def is_active(self) -> bool:
        """Check if conversation has active runtime."""
        return (self.conversation_url is not None and
                self.session_api_key is not None and
                self.sandbox_status == "RUNNING")

    def runtime_url(self) -> Optional[str]:
        """Extract runtime base URL."""
        if not self.conversation_url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(self.conversation_url)
        return f"{parsed.scheme}://{parsed.netloc}"
```

### 6.5 Trajectory Download Enhancement

V1 provides a dedicated trajectory endpoint:

```python
def get_trajectory(
    self, conversation_id: str, runtime_url: str, session_api_key: str
) -> Dict[str, Any]:
    """Download trajectory using V1 runtime API."""
    url = urljoin(runtime_url, f"api/file/download-trajectory/{conversation_id}")
    headers = {"X-Session-API-Key": session_api_key}

    response = self.session.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
```

### 6.6 Existing API Fixture Infrastructure

The project already has a comprehensive fixture recording and sanitization infrastructure that follows established patterns:

#### 6.6.1 Master Fixture Update Script

`scripts/update_fixtures.py` provides a unified workflow for updating API fixtures:

- Orchestrates both recording and sanitization phases
- Supports both V0 and V1 API versions
- Provides command-line options for selective operations (record-only, sanitize-only)
- Currently imports from V0 modules but needs V1 integration

#### 6.6.2 Version-Specific Infrastructure

**V0 Infrastructure (Established Pattern):**

- `scripts/v0/record_api_responses.py` - `APIResponseRecorder` class for V0 endpoints
- `scripts/v0/sanitize_fixtures.py` - `FixtureSanitizer` class for V0 data patterns

**V1 Infrastructure (Existing but Incomplete):**

- `scripts/v1/record_api_responses.py` - `V1APIResponseRecorder` class (needs runtime endpoint support)
- `scripts/v1/sanitize_fixtures.py` - `V1FixtureSanitizer` class (needs runtime-specific patterns)

#### 6.6.3 VCR Integration

`tests/vcr_config.py` provides VCR configuration for HTTP interaction recording:

- Sanitizes sensitive headers (`X-Session-API-Key`, `Authorization`)
- Filters sensitive request/response data
- Uses YAML serialization for readability
- Needs V1-specific sanitization patterns for runtime URLs and session keys

#### 6.6.4 Required Updates for V1 Support

1. **Master Script Integration**: Update `scripts/update_fixtures.py` to import and use V1 modules
2. **Runtime Endpoint Recording**: Enhance V1 recorder to capture runtime API interactions
3. **V1-Specific Sanitization**: Add patterns for `sandbox_id`, `conversation_url`, runtime hostnames
4. **VCR Configuration**: Extend sanitization for V1 data structures and runtime URLs

## 6. Implementation Plan

All implementations must pass existing lints and tests. New functionality requires comprehensive test coverage with both unit tests and integration tests using VCR fixtures.

### 6.1 V1 API Client Core Implementation (M1)

Complete the V1 API client with working implementations for all placeholder methods.

#### 6.1.1 Runtime URL Discovery

- `ohc/v1/api.py` - Add `extract_runtime_url()` helper method
- `tests/test_v1_api_runtime_url.py` - Test runtime URL extraction logic

#### 6.1.2 File Operations

- `ohc/v1/api.py` - Implement `get_file_content()` using `/api/file/download/{path}`
- `ohc/v1/api.py` - Implement `get_conversation_changes()` using `/api/git/changes/.`
- `tests/test_v1_api_files.py` - Test file operations with VCR fixtures

#### 6.1.3 Trajectory Operations

- `ohc/v1/api.py` - Implement `get_trajectory()` using `/api/file/download-trajectory/{id}`
- `tests/test_v1_api_trajectory.py` - Test trajectory download

#### 6.1.4 API Fixture Recording Infrastructure

- `scripts/update_fixtures.py` - Update master script to support V1 alongside existing V0 support
- `scripts/v1/record_api_responses.py` - Enhance existing V1 recorder with runtime endpoint recording
- `scripts/v1/sanitize_fixtures.py` - Update existing V1 sanitizer with runtime-specific sanitization patterns

**Demo**: Basic V1 file operations work - can download files and get git changes from active V1 conversations. API fixture infrastructure supports V1 endpoint recording and sanitization.

### 6.2 V1 Conversation Management Integration (M2)

Integrate V1 API client with existing conversation manager workflows.

#### 6.2.1 Conversation Manager V1 Support

- `conversation_manager/conversation_manager.py` - Add V1Conversation class
- `conversation_manager/conversation_manager.py` - Update conversation listing to handle V1 data structure
- `tests/test_conversation_manager_v1.py` - Test V1 conversation management

#### 6.2.2 Command Integration

- `ohc/conversation_commands.py` - Update all commands to work with V1 conversations
- `ohc/conversation_display.py` - Update display formatting for V1 conversation data
- `tests/test_v1_command_integration.py` - Test all commands work with V1 conversations

#### 6.2.3 VCR Configuration Updates

- `tests/vcr_config.py` - Extend existing VCR configuration with V1-specific sanitization patterns
- Update existing `sanitize_request()` and `sanitize_response()` functions for V1 data structures

**Demo**: All existing oh-utils commands work seamlessly with V1 conversations. VCR-based integration tests properly sanitize V1 API interactions.

### 6.3 Enhanced Error Handling and User Experience (M3)

Improve error handling and user experience for V1 conversations.

#### 6.3.1 Inactive Conversation Handling

- `ohc/v1/api.py` - Add clear error messages for inactive conversations
- `ohc/conversation_commands.py` - Add conversation activation guidance
- `tests/test_v1_inactive_conversations.py` - Test inactive conversation scenarios

#### 6.3.2 Enhanced Status Display

- `ohc/conversation_display.py` - Add sandbox status and runtime information to displays
- `conversation_manager/conversation_manager.py` - Show V1-specific status information
- `tests/test_v1_display.py` - Test enhanced display formatting

**Demo**: Users receive clear feedback about conversation states and guidance for activating inactive conversations.

### 6.4 Comprehensive Testing and Documentation (M4)

Ensure robust testing coverage and complete documentation.

#### 6.4.1 API Fixture Infrastructure Updates

- `scripts/update_fixtures.py` - Update master script to import and orchestrate V1 modules alongside V0
- `scripts/v1/record_api_responses.py` - Enhance existing V1 recorder with runtime endpoint support:
  - Add runtime API discovery from active conversations
  - Record `/api/file/download/{path}` endpoints
  - Record `/api/git/changes/.` endpoints
  - Record `/api/file/download-trajectory/{id}` endpoints
  - Handle session-based authentication with `X-Session-API-Key` headers
- `scripts/v1/sanitize_fixtures.py` - Enhance existing V1 sanitizer with runtime-specific patterns:
  - Add `sandbox_id` sanitization patterns
  - Add `conversation_url` sanitization for runtime hostnames
  - Add session API key sanitization patterns
  - Maintain consistency with V0 sanitization approach
- `tests/vcr_config.py` - Extend VCR configuration for V1 data structures:
  - Add V1 conversation data sanitization
  - Add runtime URL sanitization patterns
  - Add session key filtering for V1 authentication

#### 6.4.2 Integration Test Suite

- `tests/test_v1_integration.py` - Comprehensive integration tests covering all V1 workflows
- `tests/fixtures/v1/` - Complete VCR fixture set for all V1 API interactions using updated recording infrastructure

#### 6.4.3 Documentation Updates

- `README.md` - Update with V1 capabilities and usage examples
- `doc/v1-api-migration-guide.md` - Migration guide for V0 to V1 workflows

**Demo**: Complete V1 API integration with comprehensive test coverage and documentation, ready for production use.

## Appendix: Future Enhancement Opportunities

The V1 runtime API provides significantly more capabilities than V0. While this design focuses on functional parity, the following enhancements could be considered for future development:

### A.1 Enhanced V1 Capabilities

#### A.1.1 Bash Command Execution

- `ohc/v1/api.py` - Add `execute_bash_command()` method
- `ohc/conversation_commands.py` - Add `exec` command for direct bash execution
- `tests/test_v1_bash_execution.py` - Test bash command execution

#### A.1.2 Development Environment Access

- `ohc/v1/api.py` - Add `get_vscode_url()` and `get_desktop_url()` methods
- `ohc/conversation_commands.py` - Add `vscode` and `desktop` commands
- `tests/test_v1_dev_environment.py` - Test development environment access

#### A.1.3 Event Management

- `ohc/v1/api.py` - Add event search and management methods
- `ohc/conversation_commands.py` - Add event browsing and filtering commands
- `tests/test_v1_events.py` - Test event management functionality

#### A.1.4 Tool Integration

- `ohc/v1/api.py` - Add tool listing and management methods
- `ohc/conversation_commands.py` - Add tool discovery commands
- `tests/test_v1_tools.py` - Test tool integration

These enhancements would leverage V1's rich API to provide capabilities not available in V0, such as interactive conversation management, development environment access, and comprehensive event tracking.
