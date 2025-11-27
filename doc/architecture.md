# OpenHands Utilities Architecture Documentation

## Overview

The OpenHands Utilities project provides a comprehensive set of tools for managing OpenHands conversations and API interactions. The architecture has been refactored from a dual-implementation system to a unified, modular design that emphasizes code reuse, maintainability, and comprehensive testing.

## Architectural Principles

### 1. Single Source of Truth
All components use the same consolidated API client (`ohc.api.OpenHandsAPI`) to ensure consistent behavior and eliminate code duplication.

### 2. Modular Design
The system is organized into distinct layers with clear separation of concerns:
- **API Layer**: HTTP client and data models
- **Business Logic Layer**: Conversation management operations
- **Presentation Layer**: CLI commands and interactive interface
- **Configuration Layer**: Server and user settings management

### 3. Shared Infrastructure
Common patterns are implemented as reusable components to reduce boilerplate and ensure consistency across commands.

### 4. Comprehensive Testing
The architecture supports extensive testing through fixture-based integration tests, unit tests, and manual testing procedures.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                         │
├─────────────────────────────────────────────────────────────────┤
│  ohc CLI Commands        │  Interactive Mode    │  Legacy CLI   │
│  ├─ Server Management    │  ├─ Terminal UI      │  ├─ Compat.   │
│  ├─ Conversation Mgmt    │  ├─ Pagination       │  │   Layer    │
│  └─ Help & Utilities     │  └─ Command Loop     │  └─ Same API  │
├─────────────────────────────────────────────────────────────────┤
│                    Shared Command Infrastructure                │
├─────────────────────────────────────────────────────────────────┤
│  Command Utils           │  Configuration       │  Display      │
│  ├─ @with_server_config  │  ├─ ConfigManager    │  ├─ Formatters│
│  ├─ resolve_conv_id()    │  ├─ Server Configs   │  ├─ Tables    │
│  └─ Error Handling       │  └─ Validation       │  └─ Status    │
├─────────────────────────────────────────────────────────────────┤
│                      Unified API Client                        │
├─────────────────────────────────────────────────────────────────┤
│  OpenHandsAPI (ohc/api.py)                                     │
│  ├─ Connection Management    ├─ Conversation Operations         │
│  ├─ Authentication          ├─ Workspace Management            │
│  ├─ Error Handling          └─ Trajectory Access               │
│  └─ Type Safety                                                │
├─────────────────────────────────────────────────────────────────┤
│                      External Services                         │
├─────────────────────────────────────────────────────────────────┤
│  OpenHands API (app.all-hands.dev/api/)                       │
│  ├─ Conversations Endpoint  ├─ Workspace Endpoints            │
│  ├─ Authentication          ├─ File Downloads                  │
│  └─ Runtime Management      └─ Trajectory Data                 │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Unified API Client (`ohc/api.py`)

The `OpenHandsAPI` class serves as the single point of interaction with the OpenHands API.

**Key Features:**
- Configurable base URLs for different server environments
- Session management with automatic authentication headers
- Comprehensive error handling with user-friendly messages
- Type-safe method signatures with proper return types
- Connection testing and validation

**Methods:**
- `test_connection()`: Validate API key and server connectivity
- `search_conversations()`: List conversations with pagination
- `get_conversation()`: Retrieve detailed conversation information
- `start_conversation()`: Wake up stopped conversations
- `get_conversation_changes()`: Get workspace file changes
- `download_workspace_archive()`: Download workspace as ZIP
- `get_conversation_trajectory()`: Retrieve conversation history

### 2. Command Infrastructure (`ohc/command_utils.py`)

Shared utilities that eliminate boilerplate code across CLI commands.

**Key Components:**
- `@with_server_config`: Decorator for automatic server configuration handling
- `resolve_conversation_id()`: Centralized conversation ID resolution logic
- `handle_missing_server_config()`: Consistent error messaging
- `format_conversation_status()`: Standardized status display

**Benefits:**
- Reduces command boilerplate by >80%
- Ensures consistent error handling across all commands
- Centralizes common patterns for easier maintenance

### 3. Configuration Management (`ohc/config.py`)

Handles server configurations and user settings.

**Features:**
- JSON-based configuration storage
- Multiple server support with default selection
- Secure API key storage
- Configuration validation and migration

**Configuration Structure:**
```json
{
  "servers": {
    "production": {
      "name": "production",
      "url": "https://app.all-hands.dev/api/",
      "api_key": "your-api-key-here"
    }
  },
  "default_server": "production"
}
```

### 4. CLI Commands

#### Server Management (`ohc/server_commands.py`)
- `server add`: Add new server configurations
- `server list`: Display configured servers
- `server test`: Validate server connectivity
- `server set-default`: Set default server
- `server delete`: Remove server configurations

#### Conversation Management (`ohc/conversation_commands.py`)
- `conv list`: List conversations with pagination
- `conv show`: Display detailed conversation information
- `conv wake`: Start stopped conversations
- `conv ws-changes`: Show workspace file changes
- `conv ws-download`: Download workspace archives
- `conv trajectory`: Download conversation trajectories

### 5. Interactive Mode (`ohc/conversation_commands.py:interactive_mode()`)

Full-featured terminal interface that provides:
- Real-time conversation listing with status indicators
- Pagination for large conversation lists
- Interactive commands for all conversation operations
- Terminal-aware formatting that adapts to screen size
- Keyboard shortcuts for efficient navigation

### 6. Display Layer (`ohc/conversation_display.py`)

Handles formatting and presentation of data:
- Conversation tables with status indicators
- Detailed conversation information display
- File change summaries
- Progress indicators for downloads
- Error message formatting

### 7. Legacy Support (`conversation_manager/`)

The original conversation manager interface is maintained for backward compatibility:
- Uses the same unified API client for consistency
- Provides the same functionality as the modern CLI
- Gradually being phased out in favor of `ohc -i`

## Data Flow

### 1. Command Execution Flow
```
User Command → CLI Parser → Command Function → @with_server_config → 
ConfigManager → Server Config → API Client → OpenHands API → Response → 
Display Formatter → User Output
```

### 2. Interactive Mode Flow
```
User Input → Interactive Loop → Command Parser → Shared Command Functions → 
API Client → Response → Terminal Display → User Interface Update
```

### 3. Configuration Flow
```
User Config Command → ConfigManager → Validation → File Storage → 
Server Selection → API Client Initialization
```

## Testing Architecture

### 1. Fixture-Based Integration Testing

The project uses a sophisticated fixture-based testing system that provides:
- **Fast Execution**: No network calls during testing
- **Consistent Results**: Same responses across environments
- **Comprehensive Coverage**: Tests various API scenarios and edge cases
- **Security**: Sensitive data automatically sanitized

**Key Components:**
- `tests/fixtures/sanitized/`: Sanitized API response fixtures
- `tests/conftest.py`: Fixture loading and test configuration
- `scripts/sanitize_fixtures.py`: Automated fixture sanitization

### 2. Test Coverage Strategy

- **Unit Tests**: Individual component testing with >90% coverage for critical modules
- **Integration Tests**: API client and command infrastructure testing using fixtures
- **CLI Tests**: Command-line interface testing using Click's testing utilities
- **End-to-End Tests**: Complete workflow testing with real API interactions (optional)

### 3. Quality Gates

All code must pass:
- Linting (Ruff) with comprehensive rule set
- Type checking (MyPy) with strict settings
- Test coverage requirements (>78% overall)
- Pre-commit hooks for code quality

## Security Considerations

### 1. API Key Management
- API keys stored in local configuration files with appropriate permissions
- No API keys in code or version control
- Secure transmission using HTTPS only

### 2. Input Validation
- All user inputs validated before API calls
- Conversation ID resolution with bounds checking
- File path validation for downloads

### 3. Error Handling
- Sensitive information filtered from error messages
- Graceful degradation for network issues
- User-friendly error messages without exposing internals

## Performance Characteristics

### 1. API Client
- Session reuse for connection pooling
- Configurable timeouts and retry logic
- Efficient pagination for large conversation lists

### 2. Interactive Mode
- Lazy loading of conversation details
- Terminal-aware pagination
- Efficient screen updates

### 3. File Operations
- Streaming downloads for large workspace archives
- Progress indicators for long-running operations
- Temporary file cleanup

## Extension Points

### 1. Adding New Commands
1. Create command function in appropriate module
2. Use `@with_server_config` decorator for server handling
3. Use `resolve_conversation_id()` for conversation resolution
4. Add tests following the established patterns

### 2. Adding New API Endpoints
1. Add method to `OpenHandsAPI` class
2. Create fixtures for testing
3. Add integration tests
4. Update documentation

### 3. Custom Display Formats
1. Add formatter functions to `conversation_display.py`
2. Use consistent styling patterns
3. Support terminal width adaptation

## Migration History

The current unified architecture is the result of a systematic refactoring process:

### Milestone 1 (M1): Consolidate API Client
- Merged duplicate `OpenHandsAPI` implementations
- Preserved fixture-based testing infrastructure
- Updated legacy components to use unified client

### Milestone 2 (M2): Shared Command Infrastructure
- Created reusable command utilities and decorators
- Centralized conversation ID resolution logic
- Reduced command boilerplate by >80%

### Milestone 3 (M3): Improve Test Coverage
- Expanded test coverage from 13% to >78%
- Added comprehensive CLI command testing
- Extended fixture-based testing to all components

### Milestone 4 (M4): Documentation and Cleanup
- Created comprehensive architecture documentation
- Improved code docstrings and type annotations
- Standardized error messages and removed dead code

## Future Considerations

### 1. Potential Enhancements
- Plugin system for custom commands
- Configuration profiles for different environments
- Enhanced interactive mode with more features
- API response caching for improved performance

### 2. Maintenance
- Regular fixture updates as API evolves
- Dependency updates and security patches
- Performance monitoring and optimization
- User feedback integration

## Conclusion

The unified architecture provides a solid foundation for the OpenHands Utilities project, emphasizing maintainability, testability, and user experience. The modular design allows for easy extension while the comprehensive testing ensures reliability across different environments and use cases.