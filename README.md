# OpenHands Utilities

Administrative tools and libraries for OpenHands Cloud and Enterprise deployments.

> **Note:** These tools are for administrators and developers who need programmatic access to OpenHands. For end-user agent interactions, see the main [OpenHands CLI](https://github.com/All-Hands-AI/OpenHands) which wraps the Agent SDK.

## Packages

This monorepo contains two packages:

| Package                          | Description                                                 | Install                   |
| -------------------------------- | ----------------------------------------------------------- | ------------------------- |
| **[ohc](packages/ohc/)**         | Python library for OpenHands Cloud & Agent Server REST APIs | `uv pip install ohc`      |
| **[ohc-cli](packages/ohc-cli/)** | Administrative CLI for managing OpenHands deployments       | `uv tool install ohc-cli` |

### ohc - API Client Library

For programmatic access to OpenHands APIs:

```python
from ohc import OpenHandsAPI

api = OpenHandsAPI(api_key="your-key", version="v1")
result = api.search_conversations(limit=10)
for conv in result["results"]:
    print(f"{conv['conversation_id']}: {conv.get('title')}")
```

### ohc-cli - Command-Line Interface

For administrative tasks:

```bash
# Configure a server
ohc server add cloud https://app.all-hands.dev/api/ YOUR_API_KEY --default

# List conversations
ohc conv list

# Interactive mode
ohc -i
```

## Installation

### Install CLI (Recommended)

The CLI includes the library as a dependency:

```bash
# Install as a uv tool (recommended - isolated environment)
uv tool install ohc-cli

# Or install with pip
pip install ohc-cli
```

### Install Library Only

For programmatic use without the CLI:

```bash
uv pip install ohc
# or
pip install ohc
```

### Development Installation

```bash
git clone https://github.com/jpshackelford/oh-utils.git
cd oh-utils
uv sync --all-extras --dev
```

## Quick Start

### 1. First-time Setup: Add a Server

Before using any commands, you need to configure a server with your API token:

```bash
# Add a server configuration
ohc server add --name my-server --url https://app.all-hands.dev/api/ --apikey YOUR_API_KEY --default

# Or add interactively (will prompt for details)
ohc server add
```

**Required Information:**

- **Server name**: A friendly name for your server (e.g., "production", "my-server")
- **Server URL**: The API endpoint URL (default: `https://app.all-hands.dev/api/`)
- **API Key**: Your OpenHands API token from [https://app.all-hands.dev/settings/api-keys](https://app.all-hands.dev/settings/api-keys)

### 2. Basic Usage

```bash
# List your conversations
ohc conv list

# Show detailed info about a conversation (by number or ID)
ohc conv show 1

# Wake up a stopped conversation
ohc conv wake 2

# Download workspace files
ohc conv ws-download 1

# Start interactive mode for full-featured management
ohc -i
```

## Commands Reference

### Server Management

```bash
# Add a new server configuration
ohc server add [--name NAME] [--url URL] [--apikey KEY] [--default]

# List configured servers
ohc server list

# Test connection to a server
ohc server test [SERVER_NAME]

# Set a server as default
ohc server set-default SERVER_NAME

# Delete a server configuration
ohc server delete SERVER_NAME [--force]
```

### Conversation Management

```bash
# List conversations
ohc conv list [--server SERVER] [-n NUMBER]

# Show detailed conversation information
ohc conv show CONVERSATION_ID_OR_NUMBER [--server SERVER]

# Wake up (start) a conversation
ohc conv wake CONVERSATION_ID_OR_NUMBER [--server SERVER]

# Show conversation trajectory (action history)
ohc conv trajectory CONVERSATION_ID_OR_NUMBER [--server SERVER] [--limit N]
ohc conv traj CONVERSATION_ID_OR_NUMBER  # Short alias

# Show last N agent messages/thoughts
ohc conv tail CONVERSATION_ID_OR_NUMBER [-n NUMBER] [--server SERVER]

# Follow a conversation in real-time (like 'tail -f')
ohc conv tail CONVERSATION_ID_OR_NUMBER -f [--interval SECONDS]

# Show workspace file changes (git status)
ohc conv ws-changes CONVERSATION_ID_OR_NUMBER [--server SERVER]

# Download workspace as ZIP archive
ohc conv ws-download CONVERSATION_ID_OR_NUMBER [-o OUTPUT_FILE] [--server SERVER]
ohc conv ws-dl CONVERSATION_ID_OR_NUMBER  # Short alias
```

**Conversation ID/Number Options:**

- Use conversation number from list (e.g., `1`, `2`, `3`)
- Use full conversation ID (e.g., `a7f6c3c8-1234-5678-9abc-def012345678`)
- Use partial conversation ID (e.g., `a7f6c3c8` - must be unique)

#### Tail Follow Mode

The `tail` command supports follow mode with `-f/--follow`, similar to Unix `tail -f` for log files. This lets you monitor a conversation in real-time as new messages and thoughts appear.

```bash
# Show last message/thought
ohc conv tail <conversation-id>

# Show last 5 messages/thoughts
ohc conv tail <conversation-id> -n 5

# Follow a conversation (displays new messages as they arrive)
ohc conv tail <conversation-id> -f

# Follow with custom polling interval (default is 2 seconds)
ohc conv tail <conversation-id> -f --interval 1.0
```

Example output:

```bash
$ ohc conv tail d1849c3d -f
Following: My Conversation Title
Conversation: d1849c3d...
================================================================================
(Press Ctrl+C to stop)

Starting to analyze the codebase...
...
Found the configuration files...
...
^C
✓ Stopped following conversation
```

### Debug Tool (Enterprise)

> **Note:** The debug tool requires Kubernetes cluster access and is designed for OpenHands Enterprise deployments.

The `ohc debug` command helps troubleshoot OpenHands Enterprise deployments by providing visibility into runtime pods, cluster health, and application logs.

#### Prerequisites

- `kubectl` configured with access to your OpenHands clusters
- Kubernetes contexts set up for app and runtime clusters

#### Configuration

Before using debug commands, configure your environment:

```bash
# Interactive configuration (recommended)
ohc debug configure

# This will:
# 1. List available kubectl contexts
# 2. Auto-detect runtime configuration from runtime-api deployment
# 3. Optionally detect and configure the application endpoint
# 4. Save configuration to ~/.config/ohc/debug.json
```

**Configuration Management:**

```bash
# List configured environments
ohc debug configure --list

# Show full configuration details (includes runtime routing config)
ohc debug configure --show

# Test cluster connectivity
ohc debug configure --test

# Re-run detection to refresh configuration for an environment
ohc debug configure --refresh production

# Set default environment
ohc debug configure --default production

# Remove an environment
ohc debug configure --remove staging
```

#### Cluster Health

```bash
# Show cluster health overview
ohc debug health

# Output includes:
# - App cluster status and deployment health
# - Runtime cluster status
# - Runtime routing configuration (if detected)
# - Runtime pod summary (running, pending, errors)
# - Resource issues (OOMKilled, evicted, scheduling failures)
# - Top issues with affected runtimes

# JSON output for automation
ohc debug health --output json
```

#### Runtime Investigation

```bash
# Investigate a specific runtime by ID, session ID, or pod name
ohc debug runtime <RUNTIME_ID>

# Show with events
ohc debug runtime <RUNTIME_ID> --events

# Show with container logs
ohc debug runtime <RUNTIME_ID> --logs

# Show everything (events + logs)
ohc debug runtime <RUNTIME_ID> --all
```

#### List Runtimes

```bash
# List all runtime pods
ohc debug list

# Filter by issues
ohc debug list --errors      # Pods with errors
ohc debug list --restarts    # Pods with restarts
ohc debug list --oom         # OOMKilled pods
ohc debug list --recent      # Created in last hour

# JSON output for automation
ohc debug list --output json
```

#### App Server Diagnostics

```bash
# Show app server logs
ohc debug app logs
ohc debug app logs --since 30m --component api

# Show deployment status
ohc debug app status

# List app pods
ohc debug app pods
```

#### Multi-Environment Support

```bash
# Use specific environment
ohc debug -e staging health
ohc debug -e production list --oom

# Add additional environments
ohc debug configure --add staging
```

### Interactive Mode

Launch the full-featured interactive conversation manager:

```bash
ohc -i
```

**Interactive Commands:**

- `r` - Refresh conversation list
- `w <num>` - Wake up conversation by number (e.g., `w 3`)
- `s <num>` - Show detailed info for conversation (e.g., `s 1`)
- `f <num>` - Download workspace files for conversation (e.g., `f 1`)
- `t <num>` - Show trajectory for conversation (e.g., `t 1`)
- `a <num>` - Download entire workspace as ZIP archive (e.g., `a 1`)
- `n`, `p` - Next/previous page
- `h` - Show help
- `q` - Quit

**Features:**

- 🔐 Secure server configuration management
- 📋 List conversations with status, runtime IDs, and titles
- 🖥️ Terminal-aware formatting that adapts to screen size
- 📄 Pagination for handling large numbers of conversations
- 🔄 Real-time refresh to see updated conversation states
- ⚡ Wake up conversations by number to start inactive ones
- 🔍 Detailed conversation info with full metadata
- 📦 Download workspace archives
- 🎯 Interactive commands for easy navigation and management

## Requirements

- Python 3.8+
- requests >= 2.25.0
- click >= 8.0.0
- kubernetes >= 28.0.0 (for `ohc debug` commands)

## API Access

Get your OpenHands API token from: [https://app.all-hands.dev/settings/api-keys](https://app.all-hands.dev/settings/api-keys)

## Architecture

This is a monorepo with two independently releasable packages:

```
packages/
├── ohc/              # API client library
│   └── src/ohc/
│       ├── api.py    # Unified API client
│       ├── v0/       # V0 API implementation
│       └── v1/       # V1 API implementation
│
└── ohc-cli/          # Administrative CLI
    └── src/ohc_cli/
        ├── cli.py
        ├── conversation_commands.py
        ├── server_commands.py
        ├── debug/    # Enterprise debugging tools
        └── k8s/      # Kubernetes integration
```

### Design Principles

- **Separation of Concerns**: The library (`ohc`) has minimal dependencies (just `requests`), while the CLI (`ohc-cli`) includes heavier deps like `click` and `kubernetes`
- **Single Source of Truth**: Both packages share the same API client for consistency
- **Type Safety**: Full type annotations throughout the codebase
- **Comprehensive Testing**: Fixture-based integration tests with high coverage

## Troubleshooting

### No servers configured

If you see "No servers configured", run:

```bash
ohc server add
```

### Connection failed

- Verify your API key is correct
- Check that the server URL ends with `/api/`
- Test the connection: `ohc server test`

### Command not found

If `ohc` is not found, install it first:

```bash
uv tool install ohc-cli
```

For development, use `uv run ohc` from within the repository.

## Development

This project uses modern Python development tools and practices:

### Setup

1. **Install uv** (if not already installed):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup the development environment**:

   ```bash
   git clone <repository-url>
   cd oh-utils
   make dev-setup
   ```

   This will:
   - Install all development dependencies
   - Set up pre-commit hooks
   - Configure the development environment

### Development Tools

- **uv**: Fast Python package manager and project manager
- **pytest**: Testing framework with coverage reporting
- **ruff**: Fast Python linter and formatter (replaces flake8, isort, black)
- **mypy**: Static type checking
- **pre-commit**: Git hooks for code quality
- **commitizen**: Conventional commits and automated releases

### Available Commands

```bash
make help                 # Show all available commands
make install             # Install the package
make install-dev         # Install with development dependencies
make test                # Run tests
make test-cov            # Run tests with coverage report
make lint                # Run linting
make format              # Format code
make type-check          # Run type checking
make pre-commit          # Run pre-commit hooks on all files
make clean               # Clean build artifacts
make build               # Build the package
make release             # Create a new release (uses conventional commits)
make ci                  # Run all CI checks locally
```

### Code Quality

This project enforces high code quality standards:

- **Linting**: Ruff with comprehensive rule set
- **Formatting**: Ruff formatter (black-compatible)
- **Type Checking**: MyPy with strict settings
- **Testing**: Pytest with coverage requirements
- **Pre-commit Hooks**: Automated checks before commits

### Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning and changelog generation.

Commit message format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:

```bash
git commit -m "feat: add new conversation export feature"
git commit -m "fix: handle API timeout errors gracefully"
git commit -m "docs: update installation instructions"
```

### Automated Releases

Releases are automated using GitHub Actions:

1. **On merge to main**: If conventional commits are detected, a new version is automatically:
   - Bumped according to semantic versioning
   - Tagged in git
   - Released on GitHub with auto-generated release notes
   - Published to package repositories (placeholder implementation)

2. **Manual release**: Use `make release` locally or trigger the workflow manually

### Testing

Run tests locally:

```bash
make test          # Basic test run
make test-cov      # With coverage report
make ci            # Full CI suite (lint + type-check + test)
```

### Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes following the code quality standards
4. Write tests for new functionality
5. Use conventional commit messages
6. Submit a pull request

The CI pipeline will automatically:

- Run linting and formatting checks
- Execute the test suite across multiple Python versions
- Perform type checking
- Generate coverage reports

Each utility should be placed in its own subdirectory with appropriate documentation.

## License

MIT

This project is open source. Please check individual utility directories for specific license information.

## Links

- [OpenHands](https://www.all-hands.dev/)
- [OpenHands Documentation](https://docs.openhands.dev/)
- [API Documentation](https://docs.openhands.dev/api-reference)
