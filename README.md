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
uv run oh-conversation-manager
```

### Using pip

```bash
pip install -e .
```

## Utilities

This repository contains a comprehensive utility for working with OpenHands conversations:

### Conversation Manager

**Command:** `uv run oh-conversation-manager`

A terminal-based interactive utility for managing OpenHands conversations.

**Features:**

- 🔐 Secure API key management
- 📋 List conversations with status, runtime IDs, and titles
- 🖥️ Terminal-aware formatting that adapts to screen size
- 📄 Pagination for handling large numbers of conversations
- 🔄 Real-time refresh to see updated conversation states
- ⚡ Wake up conversations by number to start inactive ones
- 🔍 Detailed conversation info with full metadata
- 📦 Download workspace archives
- 📄 Download changed files from conversations
- 🎯 Interactive commands for easy navigation and management
- 💬 Comprehensive conversation management interface

**Quick Start:**

Using uv (recommended):

```bash
cd oh-utils
uv run oh-conversation-manager
```

Test mode (simple list):

```bash
cd oh-utils
python3 conversation_manager/conversation_manager.py --test
```

Traditional method:

```bash
python3 conversation_manager/conversation_manager.py
```

**Interactive Commands:**

- `r`, `refresh` - Refresh conversation list
- `w <num>` - Wake up conversation by number (e.g., `w 3`)
- `s <num>` - Show detailed info for conversation (e.g., `s 1`)
- `d <num>` - Download changed files for conversation (e.g., `d 1`)
- `t <num>` - Download trajectory data for conversation (e.g., `t 1`)
- `a <num>` - Download full workspace archive for conversation (e.g., `a 1`)
- `n`, `next` - Next page
- `p`, `prev` - Previous page
- `h`, `help` - Show help
- `q`, `quit` - Exit

See the [Conversation Manager README](./conversation_manager/README.md) for detailed usage instructions.

## Requirements

- Python 3.8+
- requests >= 2.25.0

## API Access

These utilities require an OpenHands API token from:
https://app.all-hands.dev/settings/api-keys

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
