# Architectural Refactoring Plan: oh-utils

**Status:** Proposed  
**Priority:** High  
**Estimated Effort:** 4-6 weeks (part-time)

---

## Overview

This plan outlines the concrete steps to address the architectural issues identified in the [Architectural Review Findings](./architectural-review-findings.md). The approach prioritizes backward compatibility and incremental progress.

---

## Phase 1: Model Layer (Priority: Critical)

**Goal:** Create typed domain models for all API entities

### 1.1 Create Directory Structure

```
ohc/
├── models/
│   ├── __init__.py
│   ├── conversation.py    # Conversation, ConversationStatus
│   ├── sandbox.py         # Sandbox, SandboxStatus, AgentServerConnection
│   ├── relationships.py   # ConversationWithSandbox (the key relationship)
│   ├── workspace.py       # WorkspaceChange, WorkspaceFile
│   ├── trajectory.py      # TrajectoryEvent, Trajectory
│   ├── events.py          # Event, EventType (V1 API)
│   └── config.py          # ServerConfig, AppConfig (unified config)
```

**Key Insight:** The Conversation↔Sandbox relationship is the core domain model that's currently missing.

### 1.2 Implement Core Models

**`ohc/models/conversation.py`**:

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

class ConversationStatus(Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
    
    @classmethod
    def from_string(cls, value: str) -> "ConversationStatus":
        try:
            return cls(value.upper())
        except ValueError:
            return cls.UNKNOWN

@dataclass
class Conversation:
    """Domain model for an OpenHands conversation."""
    
    id: str
    title: str
    status: ConversationStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    runtime_id: Optional[str] = None
    sandbox_id: Optional[str] = None  # V1 API
    url: Optional[str] = None
    session_api_key: Optional[str] = None
    version: Optional[str] = None  # conversation_version
    
    # Computed properties
    @property
    def short_id(self) -> str:
        return self.id[:8] if self.id else "unknown"
    
    @property
    def is_running(self) -> bool:
        return self.status == ConversationStatus.RUNNING
    
    @property
    def can_wake(self) -> bool:
        return self.status in (ConversationStatus.STOPPED, ConversationStatus.PAUSED)
    
    def get_runtime_base_url(self) -> Optional[str]:
        """Extract base URL for runtime API calls."""
        if not self.url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"
```

**`ohc/models/factories.py`** (API response → Model conversion):

```python
"""Factories for creating models from API responses."""

from datetime import datetime
from typing import Any, Dict, Optional

from .conversation import Conversation, ConversationStatus

def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

class ConversationFactory:
    """Factory for creating Conversation from API responses."""
    
    @staticmethod
    def from_v0_response(data: Dict[str, Any], base_url: Optional[str] = None) -> Conversation:
        """Create Conversation from V0 API response."""
        url = data.get("url")
        # Handle relative URLs
        if url and base_url and url.startswith("/"):
            from urllib.parse import urljoin
            base = base_url.rstrip("/")
            if base.endswith("/api"):
                base = base[:-4]
            url = urljoin(base, url)
        
        return Conversation(
            id=data.get("conversation_id", ""),
            title=data.get("title", "Untitled"),
            status=ConversationStatus.from_string(data.get("status", "UNKNOWN")),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("last_updated_at")),
            runtime_id=data.get("runtime_id") or _extract_runtime_id(url),
            url=url,
            session_api_key=data.get("session_api_key"),
            version=data.get("conversation_version"),
        )
    
    @staticmethod
    def from_v1_response(data: Dict[str, Any], base_url: Optional[str] = None) -> Conversation:
        """Create Conversation from V1 API response."""
        # V1 uses different field names
        status_str = data.get("sandbox_status", "UNKNOWN")
        
        return Conversation(
            id=data.get("id", ""),
            title=data.get("title", "Untitled"),
            status=ConversationStatus.from_string(status_str),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            sandbox_id=data.get("sandbox_id"),
            url=data.get("conversation_url"),
            version=data.get("conversation_version"),
        )

def _extract_runtime_id(url: Optional[str]) -> Optional[str]:
    """Extract runtime ID from conversation URL."""
    # Move existing logic from conversation_display.py
    ...
```

**`ohc/models/sandbox.py`** (Critical - Currently Missing):

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

class SandboxStatus(Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    
    @classmethod
    def from_string(cls, value: str) -> "SandboxStatus":
        try:
            return cls(value.upper())
        except ValueError:
            return cls.UNKNOWN

@dataclass
class AgentServerConnection:
    """Connection info for the Agent Server running in a sandbox."""
    url: str
    session_api_key: str
    
    @classmethod
    def from_sandbox_info(cls, sandbox: Dict[str, Any]) -> Optional["AgentServerConnection"]:
        url = sandbox.get("exposed_urls", {}).get("AGENT_SERVER")
        key = sandbox.get("session_api_key")
        if url and key:
            return cls(url=url, session_api_key=key)
        return None

@dataclass
class Sandbox:
    """A sandbox (runtime environment) that runs a conversation."""
    id: str
    status: SandboxStatus
    session_api_key: Optional[str] = None
    agent_server_url: Optional[str] = None
    vscode_url: Optional[str] = None
    
    @property
    def is_running(self) -> bool:
        return self.status == SandboxStatus.RUNNING
    
    @property
    def can_connect(self) -> bool:
        return self.is_running and self.agent_server_url is not None
    
    def get_agent_connection(self) -> Optional[AgentServerConnection]:
        if self.can_connect and self.session_api_key:
            return AgentServerConnection(
                url=self.agent_server_url,
                session_api_key=self.session_api_key
            )
        return None
```

**`ohc/models/relationships.py`** (The Key Missing Abstraction):

```python
from dataclasses import dataclass
from typing import Optional

from .conversation import Conversation
from .sandbox import Sandbox, AgentServerConnection

@dataclass
class ConversationWithSandbox:
    """
    A conversation with its associated sandbox.
    
    This is the primary working unit for most operations:
    - Displaying conversation status requires sandbox status
    - Workspace operations require agent server connection
    - Waking a conversation requires resuming its sandbox
    """
    conversation: Conversation
    sandbox: Optional[Sandbox] = None
    
    @property
    def is_active(self) -> bool:
        """Check if conversation has a running sandbox."""
        return self.sandbox is not None and self.sandbox.is_running
    
    @property
    def can_access_workspace(self) -> bool:
        """Check if workspace operations are available."""
        return self.sandbox is not None and self.sandbox.can_connect
    
    def get_agent_connection(self) -> Optional[AgentServerConnection]:
        """Get connection info for Agent Server API calls."""
        if self.sandbox:
            return self.sandbox.get_agent_connection()
        return None
```

**`ohc/models/config.py`** (Unified Config - Following debug_config.py Pattern):

```python
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

@dataclass
class ServerConfig:
    """API server configuration."""
    name: str
    url: str
    api_key: str
    is_default: bool = False
    api_version: str = "v0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "api_key": self.api_key,
            "default": self.is_default,
            "api_version": self.api_version,
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ServerConfig":
        return cls(
            name=name,
            url=data.get("url", ""),
            api_key=data.get("api_key", ""),
            is_default=data.get("default", False),
            api_version=data.get("api_version", "v0"),
        )

@dataclass
class AppConfig:
    """Root application configuration."""
    servers: Dict[str, ServerConfig] = field(default_factory=dict)
    default_server: Optional[str] = None
    
    def get_default_server(self) -> Optional[ServerConfig]:
        if self.default_server and self.default_server in self.servers:
            return self.servers[self.default_server]
        if self.servers:
            return next(iter(self.servers.values()))
        return None
```

### 1.3 Tasks

- [ ] Create `ohc/models/__init__.py`
- [ ] Create `ohc/models/conversation.py` with `Conversation`, `ConversationStatus`
- [ ] Create `ohc/models/sandbox.py` with `Sandbox`, `SandboxStatus`, `AgentServerConnection` (**Critical**)
- [ ] Create `ohc/models/relationships.py` with `ConversationWithSandbox` (**Critical**)
- [ ] Create `ohc/models/workspace.py` with `WorkspaceChange`
- [ ] Create `ohc/models/trajectory.py` with `TrajectoryEvent`
- [ ] Create `ohc/models/events.py` with `Event`, `EventType` (V1 API)
- [ ] Create `ohc/models/config.py` with `ServerConfig`, `AppConfig` (unify with debug_config pattern)
- [ ] Create `ohc/models/factories.py` with all factory methods
- [ ] Move `_extract_runtime_id_from_url()` from `conversation_display.py` to `models/factories.py`
- [ ] Write unit tests for all models and factories

### 1.4 Clarifying the Three "Runtime" Concepts

The codebase conflates three different things called "runtime":

| Concept | API Level | Model | What It Represents |
|---------|-----------|-------|-------------------|
| **Sandbox** | V1 App Server | `Sandbox` | Logical execution environment |
| **Runtime** | V0 API | (embedded in `Conversation`) | V0's name for sandbox |
| **RuntimePod** | Kubernetes | `RuntimePod` | Physical K8s pod |

The new models should clarify these relationships:

```python
# The hierarchy:
ConversationWithSandbox
├── Conversation (app-level entity)
└── Sandbox (logical runtime)
    └── may correspond to RuntimePod (k8s level, for debug commands)
```

---

## Phase 2: Services Layer (Priority: High)

**Goal:** Extract business logic from commands into reusable services

### 2.1 Create Service Classes

```
ohc/
├── services/
│   ├── __init__.py
│   ├── conversation_service.py
│   ├── workspace_service.py
│   └── trajectory_service.py
```

**`ohc/services/conversation_service.py`**:

```python
"""Conversation business logic."""

from typing import List, Optional

from ..api import OpenHandsAPI
from ..models import Conversation, ConversationFactory

class ConversationService:
    """Service for conversation operations."""
    
    def __init__(self, api: OpenHandsAPI):
        self.api = api
        self._factory = ConversationFactory()
    
    def list_conversations(self, limit: int = 20) -> List[Conversation]:
        """List conversations, returns typed models."""
        result = self.api.search_conversations(limit=limit)
        raw_convs = result.get("results", [])
        
        if self.api.version == "v0":
            return [self._factory.from_v0_response(c, self.api.base_url) for c in raw_convs]
        else:
            return [self._factory.from_v1_response(c, self.api.base_url) for c in raw_convs]
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        data = self.api.get_conversation(conversation_id)
        if not data:
            return None
        
        if self.api.version == "v0":
            return self._factory.from_v0_response(data, self.api.base_url)
        else:
            return self._factory.from_v1_response(data, self.api.base_url)
    
    def resolve_conversation(self, id_or_number: str) -> Optional[Conversation]:
        """Resolve conversation from ID, partial ID, or list number."""
        # Move logic from command_utils.resolve_conversation_id()
        # But return Conversation instead of just ID
        ...
    
    def wake_conversation(self, conversation: Conversation) -> Conversation:
        """Wake a stopped conversation."""
        if not conversation.can_wake:
            raise ValueError(f"Conversation {conversation.id} cannot be woken (status: {conversation.status})")
        
        self.api.start_conversation(conversation.id)
        # Re-fetch to get updated status
        return self.get_conversation(conversation.id)
```

### 2.2 Tasks

- [ ] Create `ohc/services/__init__.py`
- [ ] Create `ohc/services/conversation_service.py`
- [ ] Create `ohc/services/workspace_service.py`
- [ ] Create `ohc/services/trajectory_service.py`
- [ ] Move `resolve_conversation_id()` logic to `ConversationService`
- [ ] Move `filter_agent_messages()` from `conversation_commands.py` to `TrajectoryService`
- [ ] Move file download logic from `interactive.py` to `WorkspaceService`
- [ ] Write unit tests for all services

---

## Phase 3: Formatters/Output Layer (Priority: Medium)

**Goal:** Standardize output formatting across all commands

### 3.1 Create Formatter Infrastructure

```
ohc/
├── formatters/
│   ├── __init__.py
│   ├── base.py          # Protocol + Enum
│   ├── text.py          # TextFormatter
│   ├── json_fmt.py      # JsonFormatter  
│   └── table.py         # TableFormatter (optional)
```

**`ohc/formatters/base.py`**:

```python
from enum import Enum
from typing import List, Protocol

from ..models import Conversation, WorkspaceChange

class OutputFormat(Enum):
    TEXT = "text"
    JSON = "json"
    TABLE = "table"

class ConversationFormatter(Protocol):
    """Protocol for conversation formatters."""
    
    def format_conversation(self, conv: Conversation) -> str:
        """Format a single conversation."""
        ...
    
    def format_conversation_list(self, convs: List[Conversation]) -> str:
        """Format a list of conversations."""
        ...
    
    def format_conversation_details(self, conv: Conversation) -> str:
        """Format detailed conversation view."""
        ...

class WorkspaceFormatter(Protocol):
    """Protocol for workspace formatters."""
    
    def format_changes(self, changes: List[WorkspaceChange]) -> str:
        ...
```

**`ohc/formatters/text.py`**:

```python
"""Text output formatter."""

from typing import List
from ..models import Conversation, WorkspaceChange

class TextConversationFormatter:
    """Text formatter for conversations."""
    
    def format_conversation(self, conv: Conversation) -> str:
        status_icons = {
            "RUNNING": "🟢",
            "PAUSED": "🟡", 
            "STOPPED": "⚪",
            "ERROR": "🔴",
        }
        icon = status_icons.get(conv.status.value, "⚪")
        return f"{conv.short_id} {icon} {conv.status.value:12s} {conv.title}"
    
    def format_conversation_list(self, convs: List[Conversation]) -> str:
        lines = []
        for i, conv in enumerate(convs, 1):
            lines.append(f"{i:3d}. {self.format_conversation(conv)}")
        return "\n".join(lines)
```

### 3.2 Tasks

- [ ] Create `ohc/formatters/__init__.py`
- [ ] Create `ohc/formatters/base.py` with protocols
- [ ] Create `ohc/formatters/text.py`
- [ ] Create `ohc/formatters/json_fmt.py`
- [ ] Move formatting logic from `conversation_display.py`
- [ ] Move `TerminalFormatter` from `interactive.py`
- [ ] Add `--output` flag to all commands
- [ ] Write tests for formatters

---

## Phase 4: Command Layer Refactoring (Priority: Medium)

**Goal:** Simplify commands to use services and formatters

### 4.1 Create New Decorators

**`ohc/command_utils.py`** (enhanced):

```python
from functools import wraps
import click

from .formatters import OutputFormat, get_formatter
from .services import ConversationService

def with_conversation_service(func):
    """Decorator that provides a ConversationService."""
    @wraps(func)
    @with_server_config  # Chain with existing decorator
    def wrapper(api, *args, **kwargs):
        service = ConversationService(api)
        kwargs["service"] = service
        return func(*args, **kwargs)
    return wrapper

def with_output_format(func):
    """Decorator that provides a formatter based on --output flag."""
    @click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
    @wraps(func)
    def wrapper(*args, output, **kwargs):
        formatter = get_formatter(OutputFormat(output))
        kwargs["formatter"] = formatter
        return func(*args, **kwargs)
    return wrapper
```

### 4.2 Refactor Commands

**Before** (current):
```python
@conv.command()
@click.option("--server", ...)
@with_server_config
def list(api: OpenHandsAPI, server: Optional[str], limit: Optional[int]) -> None:
    try:
        result = api.search_conversations(limit=actual_limit)
        conversations = result.get("results", [])
        for i, conv_data in enumerate(conversations, 1):
            from .conversation_display import Conversation
            conv = Conversation.from_api_response(conv_data, api.base_url)
            click.echo(f"{i:2d}. {conv.short_id()} ...")
    except Exception as e:
        click.echo(f"✗ Failed: {e}", err=True)
```

**After** (refactored):
```python
@conv.command()
@click.option("--server", ...)
@with_conversation_service
@with_output_format
def list(service: ConversationService, formatter: ConversationFormatter, 
         server: Optional[str], limit: Optional[int]) -> None:
    conversations = service.list_conversations(limit=limit or 1000)
    click.echo(formatter.format_conversation_list(conversations))
```

### 4.3 Tasks

- [ ] Add `with_conversation_service` decorator
- [ ] Add `with_output_format` decorator  
- [ ] Refactor `conv list` command
- [ ] Refactor `conv show` command
- [ ] Refactor `conv wake` command
- [ ] Refactor `conv ws-download` command
- [ ] Refactor `conv trajectory` command
- [ ] Refactor `conv tail` command
- [ ] Standardize all error handling to use `click.ClickException`
- [ ] Replace all `print()` with `click.echo()`
- [ ] Update tests

---

## Phase 5: Interactive Mode Refactoring (Priority: Lower)

**Goal:** Simplify `ConversationManager` using services

### 5.1 Extract Responsibilities

Current `ConversationManager` (732 lines) should become:

```python
class ConversationManager:
    """Interactive UI controller."""
    
    def __init__(self, service: ConversationService, 
                 workspace_service: WorkspaceService,
                 formatter: TerminalFormatter):
        self.service = service
        self.workspace_service = workspace_service
        self.formatter = formatter
        # UI state only
        self.current_page = 0
        self.page_size = 20
        self.conversations: List[Conversation] = []
```

### 5.2 Tasks

- [ ] Inject `ConversationService` into `ConversationManager`
- [ ] Inject `WorkspaceService` into `ConversationManager`
- [ ] Move file-saving utilities to a separate module
- [ ] Simplify `load_conversations()` to use service
- [ ] Simplify `download_*` methods to use services
- [ ] Target: <400 lines

---

## Phase 6: API Layer Cleanup (Priority: Lower)

**Goal:** Clean up API layer after services are in place

### 6.1 Tasks

- [ ] Consider having API methods return models directly (optional)
- [ ] Remove `cast()` calls by improving type hints
- [ ] Consolidate V0/V1 differences into factories (not API wrapper)
- [ ] Add proper protocol/interface for API clients

---

## Backward Compatibility Plan

### Deprecation Strategy

1. **Keep old methods working**: Don't remove `Conversation.from_api_response()` immediately
2. **Add deprecation warnings**: Use `warnings.warn()` for old patterns
3. **Document migration**: Update docstrings with migration guidance
4. **Version it**: Major version bump when removing deprecated code

### Coexistence Period

```python
# conversation_display.py - during migration
@dataclass
class Conversation:
    # ... existing implementation
    
    @classmethod
    def from_api_response(cls, data, base_url=None):
        """
        DEPRECATED: Use ConversationFactory.from_v0_response() or from_v1_response()
        """
        import warnings
        warnings.warn(
            "Conversation.from_api_response is deprecated. "
            "Use models.factories.ConversationFactory instead.",
            DeprecationWarning,
            stacklevel=2
        )
        from .models.factories import ConversationFactory
        # Delegate to new factory
        return ConversationFactory.from_v0_response(data, base_url)
```

---

## Testing Strategy

### New Test Structure

```
tests/
├── models/
│   ├── test_conversation.py
│   ├── test_factories.py
│   └── test_workspace.py
├── services/
│   ├── test_conversation_service.py
│   └── test_workspace_service.py
├── formatters/
│   ├── test_text_formatter.py
│   └── test_json_formatter.py
└── integration/
    └── test_command_integration.py
```

### Testing Principles

1. **Models**: Unit test all computed properties and validation
2. **Factories**: Test with recorded API responses (existing fixtures)
3. **Services**: Unit test with mocked API
4. **Formatters**: Test output format correctness
5. **Commands**: Integration test with Click's CliRunner

---

## Definition of Done

### Phase 1 Complete When:
- [ ] All model classes created and tested
- [ ] Factories handle all API response variations
- [ ] No `Dict[str, Any]` types in public model APIs
- [ ] Tests pass with >90% coverage on models

### Phase 2 Complete When:
- [ ] All services created and tested
- [ ] Business logic moved out of commands
- [ ] Services use models (not dicts)
- [ ] Tests pass with >85% coverage on services

### Phase 3 Complete When:
- [ ] All formatters created
- [ ] All commands support `--output json`
- [ ] Consistent formatting across commands
- [ ] Tests pass for formatters

### Phase 4 Complete When:
- [ ] All commands use services
- [ ] All commands use formatters
- [ ] `conversation_commands.py` < 300 lines
- [ ] No `print()` statements in commands

### Phase 5 Complete When:
- [ ] `interactive.py` < 400 lines
- [ ] Uses services for all operations
- [ ] Clear separation of UI and logic

### Full Refactoring Complete When:
- [ ] All phases complete
- [ ] Documentation updated
- [ ] No deprecation warnings in core code
- [ ] Test coverage >80% overall
- [ ] CI passing

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing scripts | Keep old APIs working during transition |
| Test coverage gaps | Add tests before changing each module |
| Scope creep | Strict phase boundaries, defer nice-to-haves |
| Merge conflicts | Work in feature branches, merge frequently |
| Performance regression | Benchmark before/after key operations |

---

## Next Steps

1. Review this plan with stakeholders
2. Create GitHub issues for each phase
3. Begin Phase 1 implementation
4. Regular check-ins on progress

---

## Appendix: File Size Targets

| File | Current | Target |
|------|---------|--------|
| conversation_commands.py | 702 | <300 |
| interactive.py | 732 | <400 |
| conversation_display.py | 418 | <200 (display only) |
| api.py | 334 | <200 (after model extraction) |
| **NEW:** models/*.py | 0 | ~300 total |
| **NEW:** services/*.py | 0 | ~250 total |
| **NEW:** formatters/*.py | 0 | ~200 total |
