# Architectural Review Findings: oh-utils

**Reviewer:** AI Architecture Analysis  
**Date:** March 2026  
**Scope:** Full codebase review focusing on data models, separation of concerns, and self-similarity

---

## Executive Summary

The `oh-utils` codebase has grown organically and has several architectural inconsistencies that impede maintainability and extensibility. The core issues are:

1. **Missing Unified Data Model**: API responses are passed as `Dict[str, Any]` throughout the codebase, with ad-hoc conversion to domain objects only at the presentation layer
2. **Improper Separation of Concerns**: Business logic, data transformation, and display logic are intermingled across modules
3. **Inconsistent Patterns**: Different parts of the codebase follow different conventions for similar operations

The good news: The **debug/k8s modules** demonstrate the proper architecture pattern—they should serve as the template for refactoring the conversation management domain.

---

## Detailed Findings

### 1. Data Model Layer: The Core Problem

#### Current State

| Domain | Has Typed Model? | Where Defined | Where Used |
|--------|------------------|---------------|------------|
| Conversation | Partial | `conversation_display.py` | Display layer only |
| **Sandbox** | **No** ❌ | Returns `Dict[str, Any]` | API layer |
| **Conversation↔Sandbox** | **No relationship model** ❌ | Inline logic | v1/api.py |
| Server Config | No | Returns `Dict[str, Any]` | Everywhere as dict |
| Runtime Pod | **Yes** ✓ | `k8s/queries.py` | Throughout debug |
| Cluster Health | **Yes** ✓ | `k8s/queries.py` | Throughout debug |
| Debug Config | **Yes** ✓ | `debug_config.py` | Throughout debug |
| Detected Runtime Config | **Yes** ✓ | `k8s/detection.py` | Debug configure |
| Detected App Endpoint | **Yes** ✓ | `k8s/detection.py` | Debug configure |

#### The Sandbox/Runtime Gap - Critical Missing Model

The relationship between **Conversation** and **Sandbox** (also called "runtime" in V0) is fundamental but has no proper model:

**V0 API Concepts:**
- `Conversation` has a `runtime_id` directly embedded
- `runtime_url` points to where the runtime is running
- These are conflated concepts

**V1 API Concepts (properly separated):**
- `Conversation` has a `sandbox_id` reference
- `Sandbox` is a separate entity with:
  - `id`, `status` (STARTING, RUNNING, PAUSED, ERROR, MISSING)
  - `session_api_key` for Agent Server auth
  - `exposed_urls` dict containing `AGENT_SERVER`, `VSCODE` URLs
- The Agent Server is accessed via the Sandbox, not the Conversation

**Current Implementation Problem:**
```python
# ohc/v1/api.py lines 350-395 - Ad-hoc relationship handling
def _get_agent_server_info(self, conversation_id: str) -> tuple[str, str, Dict[str, Any]]:
    """Returns (agent_server_url, session_api_key, sandbox_info) - all raw values"""
    conversation = self.get_conversation(conversation_id)  # Dict
    sandbox_id = conversation.get("sandbox_id")  # Hope it exists
    sandbox = self.get_sandbox_info(sandbox_id)  # Another Dict
    status = sandbox.get("status", "UNKNOWN")  # Hope format is right
    agent_server_url = sandbox.get("exposed_urls", {}).get("AGENT_SERVER")  # Nested dict access
```

This should be:
```python
def get_conversation_with_sandbox(self, conversation_id: str) -> ConversationWithSandbox:
    """Returns a properly typed model with the relationship."""
    # Returns typed ConversationWithSandbox model that contains:
    # - conversation: Conversation
    # - sandbox: Optional[Sandbox]
    # - agent_server: Optional[AgentServerConnection]
```

**Why This Matters:**
1. The V0→V1 migration conflates "runtime" (V0) with "sandbox" (V1)
2. Debug commands deal with "RuntimePod" (K8s level) which is DIFFERENT from both
3. There are actually THREE concepts:
   - **Sandbox** (API level) - logical container managed by OpenHands
   - **Runtime** (V0 API) - the execution environment (conflated with sandbox)
   - **RuntimePod** (K8s level) - the actual Kubernetes pod

Without proper models, the code mixes these concepts throughout.

**The Problem**: The main conversation/API domain passes `Dict[str, Any]` everywhere:

```python
# ohc/api.py - Returns raw dicts
def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
    ...

# ohc/v1/api.py - Returns raw dicts  
def search_conversations(...) -> List[Dict[str, Any]]:
    ...

# ohc/command_utils.py - Works with raw dicts
def resolve_conversation_id(api: OpenHandsAPI, ...) -> Optional[str]:
    result = api.search_conversations(limit=100)
    conversations = result.get("results", [])  # No type safety
    conv_data = conversations[conv_number - 1]  # No type hints
    return conv_data.get("conversation_id")  # Hope it exists
```

**Contrast with the well-designed k8s module**:

```python
# ohc/k8s/queries.py - Returns proper models
@dataclass
class RuntimePod:
    name: str
    namespace: str
    runtime_id: str
    session_id: Optional[str]
    # ... 15+ typed fields with proper defaults

def get_runtime_pod(self, runtime_id: str, namespace: str) -> Optional[RuntimePod]:
    # Returns typed object, not dict
```

#### Additional Model Opportunities from Debug Commands

The debug module has well-designed models that should be templates, but there are more hiding:

| Existing Good Models | Location | What They Model |
|---------------------|----------|-----------------|
| `RuntimePod` | `k8s/queries.py` | K8s pod state |
| `ClusterHealthSummary` | `k8s/queries.py` | Aggregated health |
| `DetectedRuntimeConfig` | `k8s/detection.py` | Auto-detected K8s config |
| `DetectedAppEndpoint` | `k8s/detection.py` | Auto-detected app URL |
| `ClusterConfig` | `debug_config.py` | K8s connection info |
| `EnvironmentConfig` | `debug_config.py` | Full environment setup |
| `RuntimeRoutingConfig` | `debug_config.py` | URL routing patterns |

**Missing models that should exist:**
- `Event` - for V1 API events (currently `Dict[str, Any]`)
- `Trajectory` / `TrajectoryEvent` - for action history
- `WorkspaceChange` - for git status items
- `AgentServerConnection` - for runtime/sandbox connectivity

#### Specific Issues

1. **`Conversation` class location is wrong**:
   - Located in `conversation_display.py` (a display module)
   - Should be in a dedicated model module
   - Its `from_api_response()` method mixes parsing with business logic

2. **No Sandbox model exists**:
   - V1 API returns sandbox info as `Dict[str, Any]`
   - Status enum not typed (`STARTING`, `RUNNING`, `PAUSED`, `ERROR`, `MISSING`)
   - `exposed_urls` structure not defined
   - Relationship to Conversation is implicit

3. **API response normalization is ad-hoc**:
   ```python
   # ohc/api.py lines 91-100 - Inline transformation
   normalized_results = []
   for conv in results:
       normalized_conv = dict(conv)
       if "id" in normalized_conv and "conversation_id" not in normalized_conv:
           normalized_conv["conversation_id"] = normalized_conv["id"]
       normalized_results.append(normalized_conv)
   ```
   This should be in a model factory, not the API wrapper.

3. **No type safety across API versions**:
   - V0 API returns `{"conversation_id": ...}`
   - V1 API returns `{"id": ...}`
   - Normalization happens in multiple places inconsistently

---

### 2. Separation of Concerns: MVC Violations

#### Current Layer Structure (Problematic)

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Commands                              │
│  conversation_commands.py (702 lines)                       │
│  - CLI handling                                              │
│  - Business logic (filtering, validation)                   │
│  - Some display logic                                        │
│  - Data transformation                                       │
├─────────────────────────────────────────────────────────────┤
│                    API Layer                                 │
│  api.py → v0/api.py, v1/api.py                              │
│  - HTTP requests                                             │
│  - Response normalization (should be in model layer)        │
│  - Returns Dict[str, Any]                                   │
├─────────────────────────────────────────────────────────────┤
│                    Display Layer                             │
│  conversation_display.py                                     │
│  - Conversation MODEL (shouldn't be here)                   │
│  - URL parsing utilities (shouldn't be here)                │
│  - Display formatting (correct)                             │
│  - show_* functions that mix data fetching + display        │
└─────────────────────────────────────────────────────────────┘
```

#### What It Should Look Like

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Commands                              │
│  - Parse arguments                                           │
│  - Call services                                             │
│  - Format output (delegate to formatters)                   │
├─────────────────────────────────────────────────────────────┤
│                    Services Layer (NEW)                      │
│  - Business logic                                            │
│  - Orchestrates API calls                                    │
│  - Returns model objects                                     │
├─────────────────────────────────────────────────────────────┤
│                    Model Layer (NEW)                         │
│  - Domain models (dataclasses)                              │
│  - Factories for creating from API responses                │
│  - Validation                                                │
├─────────────────────────────────────────────────────────────┤
│                    API Layer                                 │
│  - HTTP requests only                                        │
│  - Returns raw responses (or model objects)                 │
├─────────────────────────────────────────────────────────────┤
│                    Display/Formatters                        │
│  - Rendering logic only                                      │
│  - Multiple output formats (text, json, table)              │
└─────────────────────────────────────────────────────────────┘
```

#### Specific Violations

**1. `conversation_display.py` - Display module contains non-display code**

```python
# Lines 25-116: URL parsing utilities belong in a utils module
def _get_runtime_domains() -> List[str]: ...
def _is_valid_runtime_id(value: str) -> bool: ...
def _extract_from_path(path: str) -> Optional[str]: ...
def _extract_from_subdomain(hostname: str) -> Optional[str]: ...
def _extract_runtime_id_from_url(url: str) -> Optional[str]: ...

# Lines 119-233: Model belongs in models module
@dataclass
class Conversation:
    id: str
    title: str
    # ... model + factory + methods
    
# Lines 236-408: These functions MIX data fetching with display
def show_conversation_details(api: OpenHandsAPI, conversation_id: str) -> None:
    # Calls API, transforms data, AND renders output
    data = api.get_conversation(conversation_id)
    conv = Conversation.from_api_response(data, api.base_url)
    print(f"  ID: {conv.id}")  # Display mixed with data fetching
```

**2. `conversation_commands.py` - Business logic in CLI layer**

```python
# Lines 288-298: Filter logic belongs in a service
def filter_agent_messages(trajectory_data: List[dict]) -> List[dict]:
    """Filter trajectory for agent messages and thoughts."""
    agent_messages: List[dict] = []
    for event in trajectory_data:
        is_agent = event.get("source") == "agent"
        is_message = event.get("action") == "message"
        # ... business logic in CLI layer

# Lines 425-462: Prompt processing belongs in a service
def _get_prompt_from_sources(prompt_arg: Optional[str]) -> Optional[str]:
    """Get prompt from argument, stdin, or interactive input."""
    # ... complex input handling logic
```

**3. `interactive.py` - Too many responsibilities**

The `ConversationManager` class handles:
- UI state management (good)
- API calls (should delegate to service)
- File downloads (should delegate to service)
- File saving (should be in a utility)
- Data transformation (should be in model factory)
- Display formatting (good, but could be more separated)

---

### 3. Configuration System Fragmentation

The codebase has **two completely separate configuration systems** that don't share patterns:

#### Side-by-Side Comparison

| Aspect | `config.py` (Server Config) | `debug_config.py` (Debug Config) |
|--------|----------------------------|----------------------------------|
| **Data Classes** | None - uses raw dicts | ✓ Yes - 5 dataclasses |
| **Serialization** | Manual dict manipulation | `to_dict()` / `from_dict()` methods |
| **Type Safety** | `Dict[str, Any]` everywhere | Full type hints |
| **Validation** | None | Implicit in constructors |
| **File** | `~/.config/ohc/config.json` | `~/.config/ohc/debug.json` |
| **Manager Class** | `ConfigManager` | `DebugConfigManager` |

#### config.py Issues

```python
# config.py - No models, just dict manipulation
class ConfigManager:
    def add_server(self, name: str, url: str, api_key: str, set_default: bool = False) -> None:
        config = self.load_config()  # Returns Dict[str, Any]
        config["servers"][name] = {  # Manual dict construction
            "url": url,
            "api_key": api_key,
            "default": set_default,
        }
        # No ServerConfig model, no validation
```

#### debug_config.py - The Better Pattern

```python
# debug_config.py - Proper dataclass models
@dataclass
class ClusterConfig:
    kube_context: str
    namespace: str
    
    def to_dict(self) -> Dict[str, str]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClusterConfig":
        return cls(
            kube_context=data.get("kube_context", ""),
            namespace=data.get("namespace", ""),
        )

@dataclass
class EnvironmentConfig:
    app: ClusterConfig
    runtime: Optional[ClusterConfig] = None
    routing: Optional[RuntimeRoutingConfig] = None
    # Proper composition of typed objects
```

#### The Irony

The **debug** configuration (a secondary feature) has:
- 5 well-designed dataclasses
- Proper serialization
- Type safety
- Nested object composition

The **server** configuration (the primary feature) has:
- No models
- Raw dict manipulation
- No type safety
- No validation

#### Unified Configuration Proposal

Both should use a common pattern:

```python
# ohc/models/config.py - Unified approach
@dataclass
class ServerConfig:
    """API server configuration."""
    name: str
    url: str
    api_key: str
    is_default: bool = False
    api_version: str = "v0"
    
    def to_dict(self) -> Dict[str, Any]: ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerConfig": ...

@dataclass  
class AppConfig:
    """Root application configuration."""
    servers: Dict[str, ServerConfig]
    default_server: Optional[str]
    # Could also include debug config as nested
    debug: Optional[DebugConfig] = None
```

### 4. Self-Similarity: Inconsistent Patterns

#### Output Conventions

| Module | Output Method | JSON Support |
|--------|---------------|--------------|
| server_commands.py | `click.echo()` | No |
| conversation_commands.py | Mixed `click.echo()` + `print()` | No |
| debug commands | `click.echo()` | Yes (`--output json`) |
| interactive.py | `print()` | No |

**Evidence**:
```python
# server_commands.py - Uses click.echo
click.echo(f"✓ Server '{name}' added")

# conversation_commands.py - Mixes both
click.echo(f"✗ Failed to list conversations: {e}", err=True)  # Line 65
print(f"\nConversation Details:")  # conversation_display.py line 257

# debug commands - Consistent click.echo
click.echo(f"Runtime: {pod.runtime_id}")  # runtime_cmd.py line 71
```

#### Error Handling Patterns

| Module | Pattern |
|--------|---------|
| debug commands | `raise click.ClickException(...)` |
| server_commands | `click.echo(..., err=True)` + sometimes abort |
| conversation_commands | `click.echo(..., err=True)` + return |
| API layer | `raise Exception(...)` |

#### Decorator Usage

- `@with_server_config` - Good pattern, used in conversation/server commands
- Debug commands don't use decorators, instead call `get_config_and_client()` directly
- Inconsistent approach to shared setup

#### Data Class Usage

| Domain | Pattern |
|--------|---------|
| k8s module | Full dataclasses with type hints |
| debug_config | Full dataclasses with serialization |
| conversation domain | Partial dataclass, no serialization |
| server config | No dataclass, just dicts |

---

### 4. Specific Code Smells

#### Smell 1: Cast() Overuse in API Layer

```python
# ohc/api.py - 10+ cast() calls
return cast("Dict[str, Any]", response.json())
return cast("List[Dict[str, Any]]", result["trajectory"])
return cast("V0API", self._client).search_conversations(...)
```

This indicates the type system isn't being used properly. With proper models, these would be unnecessary.

#### Smell 2: Duplicate URL Extraction Logic

The `_extract_runtime_id_from_url()` function in `conversation_display.py` is:
1. In the wrong module (display module)
2. Duplicates logic that might be needed elsewhere
3. Has no corresponding model for runtime URL information

#### Smell 3: Inconsistent Version Handling

The `api.py` wrapper has extensive conditional logic:
```python
if self.version == "v0":
    return cast("V0API", self._client).method(...)
else:
    return cast("V1API", self._client).method(...)
```

This pattern repeats for every method. A better approach would be protocol-based polymorphism or a strategy pattern.

#### Smell 4: God Class - `ConversationManager`

At 732 lines, `interactive.py`'s `ConversationManager` handles:
- Pagination state
- API calls
- File downloads
- File saving
- Display formatting
- Command parsing
- Command execution

This violates Single Responsibility Principle.

---

## Recommended Refactoring Path

### Phase 1: Create Model Layer (Week 1)

Create `ohc/models/` directory:

```python
# ohc/models/__init__.py
from .conversation import Conversation, ConversationStatus
from .workspace import WorkspaceChange, WorkspaceArchive
from .trajectory import TrajectoryEvent, Trajectory
from .config import ServerConfig

# ohc/models/conversation.py
@dataclass
class ConversationStatus(Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"

@dataclass
class Conversation:
    id: str
    title: str
    status: ConversationStatus
    runtime_id: Optional[str]
    sandbox_id: Optional[str]  # V1 only
    created_at: datetime
    updated_at: datetime
    url: Optional[str]
    session_api_key: Optional[str]
    
    @classmethod
    def from_v0_response(cls, data: Dict[str, Any]) -> "Conversation":
        """Factory for V0 API responses"""
        
    @classmethod
    def from_v1_response(cls, data: Dict[str, Any]) -> "Conversation":
        """Factory for V1 API responses"""
```

### Phase 2: Create Services Layer (Week 2)

```python
# ohc/services/conversation_service.py
class ConversationService:
    def __init__(self, api: OpenHandsAPI):
        self.api = api
    
    def list_conversations(self, limit: int = 20) -> List[Conversation]:
        """List conversations, returns typed models"""
        
    def get_conversation(self, id_or_number: str) -> Conversation:
        """Resolve and fetch conversation"""
        
    def wake_conversation(self, conversation: Conversation) -> Conversation:
        """Wake and return updated conversation"""

# ohc/services/workspace_service.py
class WorkspaceService:
    def get_changes(self, conversation: Conversation) -> List[WorkspaceChange]:
        ...
        
    def download_archive(self, conversation: Conversation, path: Path) -> Path:
        ...
```

### Phase 3: Unify Display Layer (Week 2)

```python
# ohc/formatters/__init__.py
class OutputFormat(Enum):
    TEXT = "text"
    JSON = "json"
    TABLE = "table"

class Formatter(Protocol):
    def format_conversation(self, conv: Conversation) -> str: ...
    def format_conversation_list(self, convs: List[Conversation]) -> str: ...
    
class TextFormatter(Formatter):
    ...
    
class JsonFormatter(Formatter):
    ...
```

### Phase 4: Refactor Commands (Week 3)

```python
# ohc/conversation_commands.py (simplified)
@conv.command()
@with_server_config
@with_output_format  # New decorator
def list(service: ConversationService, format: Formatter, limit: int):
    conversations = service.list_conversations(limit)
    click.echo(format.format_conversation_list(conversations))
```

### Phase 5: Standardize Patterns (Week 3-4)

1. All commands use `click.echo()`, never `print()`
2. All commands support `--output json/text` 
3. All errors use `click.ClickException`
4. All commands use decorators for common setup
5. All domain models are in `ohc/models/`

---

## Migration Strategy

### Step 1: Non-breaking additions
- Add model classes without changing existing code
- Add service layer that wraps existing API calls
- Existing code continues to work

### Step 2: Gradual migration
- Convert commands one at a time to use services
- Add `--output` flags progressively
- Update tests alongside changes

### Step 3: Cleanup
- Remove deprecated patterns
- Delete redundant code
- Update documentation

---

## Metrics for Success

| Metric | Current | Target |
|--------|---------|--------|
| Lines in conversation_commands.py | 702 | <250 |
| Lines in interactive.py | 732 | <400 |
| `Dict[str, Any]` return types | 15+ | 0 in public API |
| `cast()` calls in api.py | 10+ | 0 |
| Commands with JSON output | 3 (debug) | All |
| Modules with dataclasses | 4 | 8+ |

---

---

## 5. Test System Analysis

The test system reveals both good patterns and areas that reinforce the architectural concerns.

### Test Statistics

| Category | Files | Lines | Coverage Area |
|----------|-------|-------|---------------|
| Conversation/Display | 3 | 2,919 | Heavy mocking of `Dict[str, Any]` |
| API Integration | 4 | 1,836 | Fixture-based HTTP mocking |
| K8s/Debug | 2 | 1,194 | Tests actual dataclass models |
| Config | 2 | 822 | Good model testing pattern |
| CLI/Commands | 4 | 1,563 | Click test runner |
| **Total** | **18** | **~9,650** | |

### What the Tests Reveal About Architecture

#### 1. Fixture Structure Confirms Missing Models

The fixtures directory structure shows the Sandbox is a first-class entity in V1:

```
fixtures/v1/sanitized/
├── sandbox_info.json        # ← Sandbox is a separate entity!
├── sandbox_paused.json      # ← Sandbox has states
├── conversation_get.json    # ← Conversation references sandbox_id
└── ...
```

**Sandbox fixture content shows the needed model:**
```json
{
  "id": "SANDBOX_ID_001",
  "status": "RUNNING",
  "session_api_key": "SESSION_API_KEY_001",
  "exposed_urls": {
    "AGENT_SERVER": "https://AGENT_SERVER_HOST.runtime.all-hands.dev",
    "VSCODE": "https://VSCODE_HOST.runtime.all-hands.dev"
  }
}
```

This JSON structure should be a `Sandbox` dataclass but isn't.

#### 2. Test Patterns Differ by Domain

**K8s/Debug tests (GOOD)** - Test typed models:
```python
# tests/test_debug_config.py - Tests actual dataclasses
def test_to_dict(self) -> None:
    config = ClusterConfig(kube_context="my-context", namespace="my-namespace")
    assert config.to_dict() == {...}  # Tests model serialization

def test_from_dict(self) -> None:
    data = {"kube_context": "ctx", "namespace": "ns"}
    config = ClusterConfig.from_dict(data)  # Tests factory method
    assert config.kube_context == "ctx"
```

**Conversation tests (PROBLEMATIC)** - Test raw dicts:
```python
# tests/test_conversation_display.py - Tests with raw dicts
def test_from_api_response_with_url(self):
    api_data = {  # Raw dict, not a fixture
        "conversation_id": "api-conv-123",
        "title": "API Conversation",
        "status": "RUNNING",
        ...
    }
    conv = Conversation.from_api_response(api_data)
```

The conversation tests have to construct API response dicts inline because there's no model to test independently.

#### 3. V1 Tests Show Proper Sandbox Handling

```python
# tests/test_v1_api_integration.py
@responses.activate
def test_start_conversation_running(self, api_client, load_v1_fixture):
    conv_fixture = load_v1_fixture("conversation_get")
    sandbox_fixture = load_v1_fixture("sandbox_info")  # Separate fixture!
    
    # Must mock BOTH conversation AND sandbox endpoints
    responses.add(..., json=conv_fixture["json"])
    responses.add(..., json=sandbox_fixture["json"])
    
    result = api_client.start_conversation("CONV_ID_001")
    
    assert result["sandbox_id"] == "SANDBOX_ID_001"  # Tests relationship
    assert result["sandbox_status"] == "RUNNING"
```

This test pattern shows that Conversation and Sandbox are distinct entities with a relationship, but the code returns `Dict[str, Any]` instead of proper models.

#### 4. Test for `SandboxNotRunningError` - Good Exception Design

```python
# tests/test_v1_api_integration.py
def test_get_conversation_changes_sandbox_paused(self, api_client, load_v1_fixture):
    ...
    with pytest.raises(SandboxNotRunningError) as exc_info:
        api_client.get_conversation_changes("CONV_ID_001")
    
    assert exc_info.value.status == "PAUSED"  # Typed exception with .status
    assert "SANDBOX_ID_PAUSED" in str(exc_info.value)
```

`SandboxNotRunningError` is a well-designed exception with typed attributes - this pattern should be applied to create a `Sandbox` model.

### Good Patterns in Test System

1. **Fixture-based testing** - Recorded API responses in JSON files
2. **Separate fixtures per API version** - `fixtures/v0/` and `fixtures/v1/`
3. **Sanitization scripts** - Removes real data from fixtures
4. **VCR.py support** - Can record new interactions
5. **FixtureLoader helper class** - Clean abstraction for loading
6. **responses library mocking** - HTTP-level mocking

### Testing Gaps That Reflect Architecture Gaps

| Gap | What It Means |
|-----|---------------|
| No `Sandbox` model tests | No Sandbox model exists |
| No relationship tests | No `ConversationWithSandbox` model |
| Tests construct raw dicts | APIs return dicts, not models |
| Separate V0/V1 test files | No unified model layer to test |
| Heavy use of `MagicMock` | APIs return `Dict[str, Any]` |

### Recommendation for Test System

When implementing the model layer:

1. **Add model unit tests** like `test_debug_config.py`:
   ```python
   class TestSandbox:
       def test_is_running(self):
           sandbox = Sandbox(id="123", status=SandboxStatus.RUNNING)
           assert sandbox.is_running is True
       
       def test_from_api_response(self):
           data = load_fixture("sandbox_info")["json"]
           sandbox = SandboxFactory.from_response(data)
           assert sandbox.id == "SANDBOX_ID_001"
   ```

2. **Keep fixture-based integration tests** - They work well

3. **Add relationship tests**:
   ```python
   class TestConversationWithSandbox:
       def test_can_access_workspace_when_running(self):
           conv_with_sandbox = ConversationWithSandbox(
               conversation=Conversation(...),
               sandbox=Sandbox(status=SandboxStatus.RUNNING, agent_server_url="...")
           )
           assert conv_with_sandbox.can_access_workspace is True
   ```

---

## 6. Good Patterns to Preserve

This section documents architectural decisions and patterns that are working well and should be preserved (and expanded to other areas) during any refactoring.

### 6.1 CLI Architecture

#### Click Command Groups
The hierarchical command structure is well-designed:
```python
# ohc/cli.py - Clean entry point
@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ohc")
@click.option("--api-version", type=click.Choice(["v0", "v1"]), default="v0")
@click.pass_context
def cli(ctx: click.Context, ...):
    ctx.ensure_object(dict)
    ctx.obj["api_version"] = api_version
```

**Why it's good:**
- Context passing for shared state
- Version option built-in
- Subcommand auto-discovery
- Clean separation between `server`, `conv`, `debug` groups

#### Command Registration Pattern (Debug Module)
```python
# ohc/debug/commands.py
@click.group()
@click.option("-e", "--env", "environment", ...)
@click.pass_context
def debug(ctx: click.Context, environment: Optional[str], output: str):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["output"] = output

# Register subcommands from separate files
register_configure_command(debug)
register_runtime_command(debug)
register_health_command(debug)
register_list_command(debug)
register_app_commands(debug)
```

**Why it's good:**
- Each command in its own file
- Registration function pattern keeps imports clean
- Shared context for environment/output format
- Easy to add new commands

### 6.2 Decorator Pattern for Cross-Cutting Concerns

#### `@with_server_config` Decorator
```python
# ohc/command_utils.py
def with_server_config(func: F) -> F:
    """Decorator to handle server configuration boilerplate."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        server = kwargs.get("server")
        config_manager = ConfigManager()
        server_config = config_manager.get_server_config(server)
        
        if not server_config:
            # Handle missing config consistently
            ...
        
        api = create_api_client(server_config["api_key"], server_config["url"], api_version)
        kwargs["api"] = api
        return func(*args, **kwargs)
    return wrapper
```

**Why it's good:**
- Eliminates 6+ copies of boilerplate
- Consistent error handling
- Dependency injection of API client
- Easy to test commands in isolation

**Expand to:** Create similar decorators for `@with_conversation_service`, `@with_output_format`

### 6.3 Dataclass Model Patterns

#### Complete Model with Serialization (from debug_config.py)
```python
@dataclass
class ClusterConfig:
    """Configuration for a Kubernetes cluster connection."""
    kube_context: str
    namespace: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClusterConfig":
        return cls(
            kube_context=data.get("kube_context", ""),
            namespace=data.get("namespace", ""),
        )
```

**Why it's good:**
- Type-safe construction
- Graceful handling of missing keys with defaults
- Bidirectional serialization
- Self-documenting with docstrings

#### Domain Model with Computed Properties (from k8s/queries.py)
```python
@dataclass
class RuntimePod:
    name: str
    namespace: str
    runtime_id: str
    phase: str
    restart_count: int
    last_restart_reason: Optional[str]
    # ... more fields
    
    @property
    def is_oom_killed(self) -> bool:
        """Check if pod was OOMKilled."""
        return self.last_restart_reason == "OOMKilled"
    
    @property
    def has_errors(self) -> bool:
        """Check if pod is in error state."""
        return self.phase in ("Failed", "Unknown") or ...
    
    @property
    def age_display(self) -> str:
        """Get human-readable age."""
        if not self.created_at:
            return "unknown"
        # ... formatting logic
    
    def status_display(self) -> str:
        """Get formatted status for display."""
        if self.phase == "Running" and self.container_state == "running":
            return "🟢 Running"
        # ... more cases
```

**Why it's good:**
- Computed properties encapsulate logic
- Display methods on models (not just in formatters)
- Optional fields with sensible defaults
- Business logic (`is_oom_killed`) lives with data

### 6.4 Module Organization

#### K8s Module Layering
```
ohc/k8s/
├── __init__.py      # Public API exports
├── client.py        # Low-level K8s API wrapper (403 lines)
├── queries.py       # Domain queries and models (454 lines)
└── detection.py     # Auto-detection logic (398 lines)
```

**Why it's good:**
- Clear separation: client (HTTP) → queries (domain) → detection (discovery)
- Each file has single responsibility
- Models live with their queries
- `__init__.py` controls public API

#### Debug Module Command Organization
```
ohc/debug/
├── __init__.py        # Exports debug group
├── commands.py        # Main group, registers subcommands
├── utils.py           # Shared utilities
├── configure_cmd.py   # ohc debug configure
├── runtime_cmd.py     # ohc debug runtime
├── health_cmd.py      # ohc debug health
├── list_cmd.py        # ohc debug list
└── app_cmd.py         # ohc debug app
```

**Why it's good:**
- One command per file
- Shared utilities extracted
- Main file just orchestrates
- Easy to find and modify commands

### 6.5 Configuration Management

#### XDG Base Directory Compliance
```python
def _get_config_dir(self) -> Path:
    """Get configuration directory following XDG Base Directory Specification."""
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "ohc"
    return Path.home() / ".config" / "ohc"
```

**Why it's good:**
- Respects user's XDG_CONFIG_HOME
- Sensible default fallback
- Standard Linux convention

#### Secure File Permissions
```python
def save_config(self, config: Dict[str, Any]) -> None:
    with open(self.config_file, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(self.config_file, 0o600)  # Only owner can read/write
```

**Why it's good:**
- API keys protected from other users
- Standard security practice

### 6.6 Testing Patterns

#### Fixture-Based Integration Testing
```python
# tests/conftest.py
class FixtureLoader:
    """Helper class for loading and managing test fixtures."""
    
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def load(self, fixture_name: str) -> Dict[str, Any]:
        """Load a fixture by name, with caching."""
        if fixture_name not in self._cache:
            fixture_file = self.fixtures_dir / f"{fixture_name}.json"
            with open(fixture_file) as f:
                self._cache[fixture_name] = json.load(f)
        return self._cache[fixture_name]
```

**Why it's good:**
- Caching prevents repeated file reads
- Clear naming convention
- Separate fixtures per API version

#### Fixture Sanitization Pipeline
```
scripts/
├── record_api_responses.py   # Record real API responses
├── sanitize_fixtures.py      # Remove sensitive data
└── update_fixtures.py        # Combined workflow
```

**Why it's good:**
- Real data never in version control
- Reproducible sanitization
- Easy to update when API changes

#### Responses Library for HTTP Mocking
```python
@responses.activate
def test_search_conversations(self, api_client, fixture_loader):
    fixture = fixture_loader.load("conversations_list_success")
    responses.add(
        responses.GET,
        "https://app.all-hands.dev/api/conversations",
        json=fixture["response"]["json"],
        status=fixture["response"]["status_code"],
    )
    
    result = api_client.search_conversations(limit=5)
    assert isinstance(result, dict)
```

**Why it's good:**
- HTTP-level mocking (not patching internals)
- Real request/response cycle
- Fixtures match actual API format

### 6.7 Error Handling Patterns

#### Typed Exception with Context
```python
# ohc/v1/api.py
class SandboxNotRunningError(Exception):
    """Raised when a sandbox operation requires a running sandbox."""
    
    def __init__(self, sandbox_id: str, status: str, message: Optional[str] = None):
        self.sandbox_id = sandbox_id
        self.status = status
        default_msg = f"Sandbox {sandbox_id} is not running (status: {status})"
        self.message = message or default_msg
        super().__init__(self.message)
```

**Why it's good:**
- Typed attributes for programmatic handling
- Good default message
- Can be caught specifically

#### Graceful Degradation
```python
# ohc/conversation_display.py
def show_conversation_details(api: OpenHandsAPI, conversation_id: str) -> None:
    # If runtime_id is not available, try fetching from runtime config endpoint
    if not conv.runtime_id and conv.status == "RUNNING":
        try:
            runtime_config = api.get_runtime_config(conversation_id)
            if runtime_config and "runtime_id" in runtime_config:
                conv.runtime_id = runtime_config["runtime_id"]
        except Exception as e:
            logger.debug(f"Could not fetch runtime config for {conv.id}: {e}")
            # Continue without runtime_id - don't fail the whole operation
```

**Why it's good:**
- Try alternative approaches
- Log for debugging
- Don't fail entire operation for optional data

### 6.8 Display and Formatting

#### TerminalFormatter Class
```python
# ohc/interactive.py
class TerminalFormatter:
    """Handles terminal formatting and display"""
    
    def __init__(self) -> None:
        self.terminal_size = self.get_terminal_size()
    
    def get_terminal_size(self) -> Tuple[int, int]:
        try:
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except Exception:
            return 80, 24  # Default fallback
    
    def format_conversations_table(self, conversations: List[Conversation], ...) -> List[str]:
        # Adapts to terminal width
        ...
```

**Why it's good:**
- Separated formatting from business logic
- Terminal-aware with fallbacks
- Returns strings (pure function), doesn't print

#### Status Icons and Emojis
```python
status_icons = {
    "M": "📝",  # Modified
    "A": "➕",  # Added/New
    "D": "🗑️",  # Deleted
    "U": "⚠️",  # Unmerged/Conflict
}

def status_display(self) -> str:
    if self.phase == "Running" and self.container_state == "running":
        return "🟢 Running"
    elif self.phase == "Pending":
        return "🟡 Pending"
```

**Why it's good:**
- Visual scanning is faster
- Consistent iconography
- Method on model, not scattered in commands

### 6.9 API Client Design

#### Session Reuse
```python
def __init__(self, api_key: str, base_url: str = "..."):
    self.session = requests.Session()
    self.session.headers.update({
        "X-Session-API-Key": api_key,
        "Content-Type": "application/json"
    })
```

**Why it's good:**
- Connection pooling
- Headers set once
- More efficient than per-request

#### URL Construction
```python
from urllib.parse import urljoin

url = urljoin(self.base_url, f"conversations/{conversation_id}")
```

**Why it's good:**
- Handles trailing slashes correctly
- Standard library, well-tested

### 6.10 Type Annotations

The codebase has good type annotation coverage:

```python
def search_conversations(
    self,
    query: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
```

**Why it's good:**
- IDE support and autocomplete
- Catches errors at development time
- Self-documenting

**Note:** The `Dict[str, Any]` return types are a problem (as noted in findings), but the practice of annotating is good.

---

## Summary: Patterns to Expand

| Good Pattern | Currently In | Expand To |
|--------------|--------------|-----------|
| Dataclass models | debug_config, k8s | conversation, sandbox, config |
| to_dict/from_dict | debug_config | all models |
| Computed properties | RuntimePod | Conversation, Sandbox |
| Command per file | debug/* | conversation/* |
| @decorator for setup | command_utils | services, formatters |
| Typed exceptions | SandboxNotRunningError | more domain errors |
| TerminalFormatter | interactive | shared formatters module |
| Fixture-based tests | API tests | model tests, service tests |

---

## Conclusion

The `oh-utils` codebase has solid foundations in some areas (debug/k8s) but needs significant refactoring in the core conversation management domain. The recommended approach is to:

1. Use the well-designed debug/k8s modules as templates
2. Introduce proper model and service layers
3. Gradually migrate existing code to new patterns
4. Standardize output and error handling

The refactoring can be done incrementally without breaking existing functionality, making it a low-risk improvement path.
