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

We propose a comprehensive V1 API integration that leverages the full capabilities of the V1 runtime agent server while maintaining compatibility with existing workflows. The solution will:

1. **Implement proper V1 conversation discovery**: Use `/api/v1/app-conversations/search` to list conversations and extract runtime URLs from active conversations
2. **Complete V1 API client implementation**: Replace `NotImplementedError` placeholders with working implementations using V1 runtime endpoints
3. **Enhance functionality beyond V0 capabilities**: Leverage V1's rich API for bash execution, event management, tool integration, and development environment access
4. **Address the workspace ZIP gap**: Implement alternative approaches for workspace archiving using V1's file download capabilities
5. **Maintain backward compatibility**: Ensure existing oh-utils commands work seamlessly with V1 conversations

The design prioritizes leveraging V1's enhanced capabilities while providing a smooth migration path from V0 workflows.

## 2. User Interface

Users will experience enhanced functionality with V1 conversations while maintaining familiar command patterns:

### 2.1 Enhanced Conversation Listing
```bash
# List conversations shows V1 conversations with sandbox information
$ oh-conversation-manager list
ID       Title                                    Status    Runtime   Sandbox
71468a85 Investigate V1 runtime API server       PAUSED    dxtugal   5MRNMGg
befbbf34 Test V1 conversation functionality      RUNNING   dxtugal   3Yn2ncz
```

### 2.2 Enhanced File Operations
```bash
# Download files with improved error handling and progress
$ oh-conversation-manager download-files 71468a85
🔍 Fetching list of changed files...
📄 Found 12 changed files
📁 Downloading files to: files-71468a85-20231203-092000/
✅ Downloaded: src/api.py (2.3 KB)
✅ Downloaded: tests/test_api.py (5.1 KB)
...
```

### 2.3 New Capabilities
```bash
# Execute bash commands directly (V1 only)
$ oh-conversation-manager exec 71468a85 "ls -la"
total 48
drwxr-xr-x  8 user user 4096 Dec  3 09:20 .
drwxr-xr-x  3 user user 4096 Dec  3 09:15 ..
-rw-r--r--  1 user user 1234 Dec  3 09:20 README.md

# Access development environment (V1 only)
$ oh-conversation-manager vscode 71468a85
🌐 VSCode URL: https://dxtugalgwuthebpf.prod-runtime.all-hands.dev/vscode
```

## 3. Other Context

### 3.1 V1 Runtime Agent Server Architecture

V1 conversations run on a sophisticated runtime agent server that provides a comprehensive REST API. The server is built with FastAPI and includes:

- **Event System**: Complete event tracking and management
- **File Operations**: Upload/download with path-based access
- **Bash Integration**: Direct command execution and event logging  
- **Development Tools**: VSCode and desktop environment access
- **Git Operations**: Enhanced git change tracking and diff capabilities
- **Tool Management**: Access to available AI tools and capabilities

### 3.2 Authentication and Session Management

V1 runtime APIs use session-based authentication where active conversations provide a `session_api_key` that must be included in runtime API calls via the `X-Session-API-Key` header.

### 3.3 Conversation Lifecycle

V1 conversations have distinct states:
- **PAUSED**: Conversation exists but runtime is not active (`conversation_url` is null)
- **RUNNING**: Conversation is active with runtime server (`conversation_url` points to runtime)
- **STOPPED**: Conversation is terminated

## 4. Technical Design

### 4.1 V1 Conversation Discovery and Runtime URL Extraction

#### 4.1.1 Conversation Data Structure

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

#### 4.1.2 Runtime URL Extraction Logic

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

### 4.2 V1 API Client Implementation

#### 4.2.1 Core Methods Implementation

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

#### 4.2.2 Enhanced V1-Specific Methods

```python
def execute_bash_command(
    self, conversation_id: str, command: str, runtime_url: str, session_api_key: str
) -> Dict[str, Any]:
    """Execute bash command using V1 runtime API."""
    url = urljoin(runtime_url, "api/bash/execute_bash_command")
    headers = {"X-Session-API-Key": session_api_key}
    data = {"command": command}
    
    response = self.session.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def get_vscode_url(self, runtime_url: str, session_api_key: str) -> str:
    """Get VSCode URL for development environment access."""
    url = urljoin(runtime_url, "api/vscode/url")
    headers = {"X-Session-API-Key": session_api_key}
    
    response = self.session.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["url"]
```

### 4.3 Workspace Archive Alternative

Since V1 lacks a direct workspace ZIP endpoint, implement a comprehensive file-based approach:

#### 4.3.1 File Discovery and Download

```python
def download_workspace_archive_v1(
    self, conversation_id: str, runtime_url: str, session_api_key: str
) -> bytes:
    """Create workspace archive by downloading all changed files."""
    # Get list of all changed files
    changes = self.get_conversation_changes(conversation_id, runtime_url, session_api_key)
    
    # Create ZIP archive in memory
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for change in changes:
            file_path = change["file"]
            try:
                content = self.get_file_content(conversation_id, file_path, runtime_url, session_api_key)
                zip_file.writestr(file_path, content)
            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Could not download {file_path}: {e}")
    
    return zip_buffer.getvalue()
```

### 4.4 Enhanced Conversation Management

#### 4.4.1 V1 Conversation Class

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

### 4.5 Trajectory Download Enhancement

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

## 5. Implementation Plan

All implementations must pass existing lints and tests. New functionality requires comprehensive test coverage with both unit tests and integration tests using VCR fixtures.

### 5.1 V1 API Client Core Implementation (M1)

Complete the V1 API client with working implementations for all placeholder methods.

#### 5.1.1 Runtime URL Discovery
* `ohc/v1/api.py` - Add `extract_runtime_url()` helper method
* `tests/test_v1_api_runtime_url.py` - Test runtime URL extraction logic

#### 5.1.2 File Operations
* `ohc/v1/api.py` - Implement `get_file_content()` using `/api/file/download/{path}`
* `ohc/v1/api.py` - Implement `get_conversation_changes()` using `/api/git/changes/.`
* `tests/test_v1_api_files.py` - Test file operations with VCR fixtures

#### 5.1.3 Trajectory Operations  
* `ohc/v1/api.py` - Implement `get_trajectory()` using `/api/file/download-trajectory/{id}`
* `tests/test_v1_api_trajectory.py` - Test trajectory download

**Demo**: Basic V1 file operations work - can download files and get git changes from active V1 conversations.

### 5.2 Workspace Archive Alternative (M2)

Implement comprehensive workspace archiving for V1 conversations.

#### 5.2.1 File-Based Archive Creation
* `ohc/v1/api.py` - Implement `download_workspace_archive()` using file enumeration and ZIP creation
* `tests/test_v1_workspace_archive.py` - Test archive creation with multiple files

#### 5.2.2 Error Handling and Progress
* `ohc/v1/api.py` - Add robust error handling for missing files
* `ohc/v1/api.py` - Add progress reporting for large workspaces

**Demo**: Can create complete workspace archives from V1 conversations, handling missing files gracefully.

### 5.3 Enhanced V1 Capabilities (M3)

Leverage V1-specific features not available in V0.

#### 5.3.1 Bash Command Execution
* `ohc/v1/api.py` - Add `execute_bash_command()` method
* `ohc/conversation_commands.py` - Add `exec` command for direct bash execution
* `tests/test_v1_bash_execution.py` - Test bash command execution

#### 5.3.2 Development Environment Access
* `ohc/v1/api.py` - Add `get_vscode_url()` and `get_desktop_url()` methods  
* `ohc/conversation_commands.py` - Add `vscode` and `desktop` commands
* `tests/test_v1_dev_environment.py` - Test development environment access

**Demo**: Users can execute bash commands and access development environments directly from oh-utils.

### 5.4 V1 Conversation Management Integration (M4)

Integrate V1 API client with existing conversation manager workflows.

#### 5.4.1 Conversation Manager V1 Support
* `conversation_manager/conversation_manager.py` - Add V1Conversation class
* `conversation_manager/conversation_manager.py` - Update conversation listing to handle V1 data structure
* `tests/test_conversation_manager_v1.py` - Test V1 conversation management

#### 5.4.2 Command Integration
* `ohc/conversation_commands.py` - Update all commands to work with V1 conversations
* `ohc/conversation_display.py` - Update display formatting for V1 conversation data
* `tests/test_v1_command_integration.py` - Test all commands work with V1 conversations

**Demo**: All existing oh-utils commands work seamlessly with V1 conversations, with enhanced capabilities where available.

### 5.5 Enhanced Error Handling and User Experience (M5)

Improve error handling and user experience for V1 conversations.

#### 5.5.1 Inactive Conversation Handling
* `ohc/v1/api.py` - Add clear error messages for inactive conversations
* `ohc/conversation_commands.py` - Add conversation activation guidance
* `tests/test_v1_inactive_conversations.py` - Test inactive conversation scenarios

#### 5.5.2 Enhanced Status Display
* `ohc/conversation_display.py` - Add sandbox status and runtime information to displays
* `conversation_manager/conversation_manager.py` - Show V1-specific status information
* `tests/test_v1_display.py` - Test enhanced display formatting

**Demo**: Users receive clear feedback about conversation states and guidance for activating inactive conversations.

### 5.6 Comprehensive Testing and Documentation (M6)

Ensure robust testing coverage and complete documentation.

#### 5.6.1 Integration Test Suite
* `tests/test_v1_integration.py` - Comprehensive integration tests covering all V1 workflows
* `tests/fixtures/v1/` - Complete VCR fixture set for all V1 API interactions
* `scripts/v1/record_api_responses.py` - Script for recording V1 API fixtures

#### 5.6.2 Documentation Updates
* `README.md` - Update with V1 capabilities and usage examples
* `doc/v1-api-migration-guide.md` - Migration guide for V0 to V1 workflows
* `doc/v1-enhanced-features.md` - Documentation of V1-specific enhanced features

**Demo**: Complete V1 API integration with comprehensive test coverage and documentation, ready for production use.