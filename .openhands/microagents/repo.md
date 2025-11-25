# Repository Purpose

This project is a collection of utilities for working with OpenHands (formerly All-Hands-AI / OpenDevin) API and conversations. The main utility is a terminal-based interactive conversation manager that allows users to manage OpenHands conversations, download workspace archives, and handle conversation data.

# Setup Instructions

This project uses modern Python development tools with uv as the package manager:

1. **Install uv** (if not already installed):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Development setup**:

   ```bash
   make dev-setup
   ```

   This installs all dependencies and sets up pre-commit hooks.

3. **Quick installation**:

   ```bash
   uv pip install -e .
   ```

4. **Run the main utility**:
   ```bash
   uv run oh-conversation-manager
   ```

# Repository Structure

- `/conversation_manager/`: Main conversation manager utility with terminal-based interface
- `/ohc/`: OpenHands CLI utility module
- `/tests/`: Comprehensive test suite with integration tests
- `/scripts/`: Development and maintenance scripts
- `/doc/`: Documentation files
- `/.github/`: CI/CD workflows and issue templates
- `pyproject.toml`: Project configuration with dependencies and tool settings
- `Makefile`: Development commands and shortcuts
- `.pre-commit-config.yaml`: Pre-commit hooks configuration

# CI/CD Workflows

- `ci.yml`: Main CI pipeline that runs linting, type checking, and tests across multiple Python versions (3.9-3.12) and operating systems (Ubuntu, Windows, macOS)
- `pre-commit.yml`: Runs pre-commit hooks on pull requests
- `release.yml`: Automated release workflow using conventional commits
- `test-release.yml`: Test release workflow

# Development Tools and Quality Standards

- **uv**: Fast Python package manager and project manager
- **pytest**: Testing framework with coverage reporting and XML output
- **ruff**: Fast Python linter and formatter (replaces flake8, isort, black)
- **mypy**: Static type checking with strict settings
- **pre-commit**: Git hooks for code quality enforcement
- **commitizen**: Conventional commits and automated releases

# Pre-commit Hooks

The project uses comprehensive pre-commit hooks that run automatically before commits:

- **Code Quality**: Ruff linting and formatting, MyPy type checking
- **File Checks**: Trailing whitespace, end-of-file-fixer, YAML/TOML/JSON validation
- **Security**: Check for debug statements, large files, merge conflicts
- **Commit Standards**: Commitizen for conventional commit message format
- **Documentation**: Prettier formatting for Markdown, YAML, and JSON files

# Development Guidelines

- Always ensure tests pass before committing: `make test` or `make ci`
- Use conventional commit messages for automated versioning
- Run the full CI suite locally before pushing: `make ci`
- Pre-commit hooks are automatically installed with `make dev-setup`
- Code coverage is tracked and reported in CI
- Type checking is enforced with MyPy
- All code must pass Ruff linting and formatting checks

# API Requirements

These utilities require an OpenHands API token from: https://app.all-hands.dev/settings/api-keys

# Testing

- Unit tests with pytest and coverage reporting
- Integration tests for API functionality
- Test fixtures and VCR for API response recording
- Cross-platform testing (Ubuntu, Windows, macOS)
- Multiple Python version support (3.8+, tested on 3.9-3.12)

# Design Documents

When creating design documents for this repository, use the template located at:

`.openhands/templates/design-document-template.md`

This template provides a structured format for documenting technical designs, including problem statements, proposed solutions, technical specifications, and implementation plans.

To use the template:

```bash
cp .openhands/templates/design-document-template.md path/to/your-design-doc.md
```
