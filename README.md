# OpenHands Utilities

A collection of utilities for working with OpenHands (formerly All-Hands-AI / OpenDevin) API and conversations.

## Installation

### Using uv (Recommended)

Install using uv:

```bash
uv pip install -e .
```

Or run directly without installation:

```bash
uv run ohc
```

### Using pip

```bash
pip install -e .
```

## Quick Start

### 1. First-time Setup: Add a Server

Before using any commands, you need to configure a server with your API token:

```bash
# Add a server configuration
uv run ohc server add --name my-server --url https://app.all-hands.dev/api/ --apikey YOUR_API_KEY --default

# Or add interactively (will prompt for details)
uv run ohc server add
```

**Required Information:**
- **Server name**: A friendly name for your server (e.g., "production", "my-server")
- **Server URL**: The API endpoint URL (default: `https://app.all-hands.dev/api/`)
- **API Key**: Your OpenHands API token from [https://app.all-hands.dev/settings/api-keys](https://app.all-hands.dev/settings/api-keys)

### 2. Basic Usage

```bash
# List your conversations
uv run ohc conv list

# Show detailed info about a conversation (by number or ID)
uv run ohc conv show 1

# Wake up a stopped conversation
uv run ohc conv wake 2

# Download workspace files
uv run ohc conv ws-download 1

# Start interactive mode for full-featured management
uv run ohc -i
```

## Commands Reference

### Server Management

```bash
# Add a new server configuration
uv run ohc server add [--name NAME] [--url URL] [--apikey KEY] [--default]

# List configured servers
uv run ohc server list

# Test connection to a server
uv run ohc server test [SERVER_NAME]

# Set a server as default
uv run ohc server set-default SERVER_NAME

# Delete a server configuration
uv run ohc server delete SERVER_NAME [--force]
```

### Conversation Management

```bash
# List conversations
uv run ohc conv list [--server SERVER] [-n NUMBER]

# Show detailed conversation information
uv run ohc conv show CONVERSATION_ID_OR_NUMBER [--server SERVER]

# Wake up (start) a conversation
uv run ohc conv wake CONVERSATION_ID_OR_NUMBER [--server SERVER]

# Show conversation trajectory (action history)
uv run ohc conv trajectory CONVERSATION_ID_OR_NUMBER [--server SERVER] [--limit N]
uv run ohc conv traj CONVERSATION_ID_OR_NUMBER  # Short alias

# Show workspace file changes (git status)
uv run ohc conv ws-changes CONVERSATION_ID_OR_NUMBER [--server SERVER]

# Download workspace as ZIP archive
uv run ohc conv ws-download CONVERSATION_ID_OR_NUMBER [-o OUTPUT_FILE] [--server SERVER]
uv run ohc conv ws-dl CONVERSATION_ID_OR_NUMBER  # Short alias
```

**Conversation ID/Number Options:**
- Use conversation number from list (e.g., `1`, `2`, `3`)
- Use full conversation ID (e.g., `a7f6c3c8-1234-5678-9abc-def012345678`)
- Use partial conversation ID (e.g., `a7f6c3c8` - must be unique)

### Interactive Mode

Launch the full-featured interactive conversation manager:

```bash
uv run ohc -i
```

**Interactive Commands:**
- `r` - Refresh conversation list
- `w <num>` - Wake up conversation by number (e.g., `w 3`)
- `s <num>` - Show detailed info for conversation (e.g., `s 1`)
- `f <num>` - Download workspace files for conversation (e.g., `f 1`)
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

## API Access

Get your OpenHands API token from: [https://app.all-hands.dev/settings/api-keys](https://app.all-hands.dev/settings/api-keys)

## Legacy Command

The original conversation manager is still available as:

```bash
uv run oh-conversation-manager
```

However, we recommend using the new `ohc` CLI for better functionality and server management.

## Troubleshooting

### No servers configured
If you see "No servers configured", run:
```bash
uv run ohc server add
```

### Connection failed
- Verify your API key is correct
- Check that the server URL ends with `/api/`
- Test the connection: `uv run ohc server test`

### Command not found
Make sure you're in the project directory and using `uv run ohc` or install the package first.

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
