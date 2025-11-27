# Multi-Command CLI Restructure: OpenHands Cloud (ohc)

## 1. Introduction

### 1.1 Problem Statement

The current OpenHands utilities package provides a single-purpose conversation manager CLI tool (`oh-conversation-manager`) with limited functionality and no extensibility for additional commands. Users must remember a long command name and cannot easily discover or access related functionality. The tool lacks proper server configuration management, requiring users to manually handle API keys and endpoints each time they use the tool.

### 1.2 Proposed Solution

We propose restructuring the command line utility into a multi-command CLI named "ohc" (OpenHands Cloud) that provides:

1. **Intuitive command structure**: `ohc <command> [subcommand] [options]` instead of a single monolithic tool
2. **Server configuration management**: `ohc server add/list/delete` commands to manage multiple OpenHands server endpoints
3. **Persistent configuration**: Server configurations stored in `~/.config/ohc/` with support for default servers
4. **Interactive mode as default**: Simplified user experience with `ohc -i` for explicit interactive mode
5. **Standard CLI conventions**: `--version`, `--help`, and other expected CLI behaviors

The new structure enables future expansion with additional command groups while maintaining backward compatibility through the existing conversation management functionality.

## 2. User Interface

### 2.1 Basic Commands

```bash
# Version and help
ohc --version
ohc --help

# Interactive mode (default behavior)
ohc
ohc -i

# Server management
ohc server add --name prod --url https://app.all-hands.dev/api/ --apikey sk-... --default
ohc server add  # Interactive prompts for required parameters
ohc server list
ohc server delete prod
ohc server set-default staging

# Conversation management (existing functionality)
ohc conversations list
ohc conversations wake 3
ohc conversations download 1
```

### 2.2 Server Configuration Workflow

**Adding a server with all parameters:**

```bash
$ ohc server add --name production --url https://app.all-hands.dev/api/ --apikey sk-abc123 --default
✓ Testing connection to https://app.all-hands.dev/api/...
✓ Connection successful
✓ Server 'production' added and set as default
```

**Adding a server interactively:**

```bash
$ ohc server add
Server name: staging
Server URL: https://staging.all-hands.dev/api/
API Key: sk-def456
Set as default? [y/N]: n
✓ Testing connection to https://staging.all-hands.dev/api/...
✓ Connection successful
✓ Server 'staging' added
```

**Listing servers:**

```bash
$ ohc server list
* production  https://app.all-hands.dev/api/     (default)
  staging     https://staging.all-hands.dev/api/
```

## 3. Other Context

### 3.1 Click Framework

We will use the Click framework for building the multi-command CLI as it provides:

- Automatic help generation
- Command grouping and nesting
- Parameter validation and type conversion
- Interactive prompts
- Consistent error handling

Click installation: `pip install click`

### 3.2 Configuration Storage

Following XDG Base Directory Specification, configuration will be stored in:

- Primary: `~/.config/ohc/config.json`
- Fallback: `~/.ohc/config.json` (for systems without XDG support)

Configuration format:

```json
{
  "servers": {
    "production": {
      "url": "https://app.all-hands.dev/api/",
      "api_key": "sk-abc123",
      "default": true
    },
    "staging": {
      "url": "https://staging.all-hands.dev/api/",
      "api_key": "sk-def456",
      "default": false
    }
  },
  "default_server": "production"
}
```

## 4. Technical Design

### 4.1 Project Structure

The new structure will organize code as follows:

```
oh-utils/
├── ohc/
│   ├── __init__.py
│   ├── cli.py              # Main CLI entry point
│   ├── config.py           # Configuration management
│   ├── server_commands.py  # Server management commands
│   ├── conversation_commands.py  # Conversation management commands
│   └── api.py              # Refactored API client
├── conversation_manager/   # Legacy module (deprecated)
└── pyproject.toml         # Updated entry points
```

### 4.2 CLI Architecture

```python
# ohc/cli.py
import click
from .server_commands import server
from .conversation_commands import conversations

@click.group()
@click.version_option()
@click.option('-i', '--interactive', is_flag=True, help='Run in interactive mode')
@click.pass_context
def cli(ctx, interactive):
    """OpenHands Cloud CLI - Manage OpenHands servers and conversations."""
    ctx.ensure_object(dict)
    ctx.obj['interactive'] = interactive

    # If no subcommand and interactive mode, start conversation manager
    if ctx.invoked_subcommand is None:
        from .conversation_commands import interactive_mode
        interactive_mode()

cli.add_command(server)
cli.add_command(conversations)
```

### 4.3 Configuration Management

```python
# ohc/config.py
import json
import os
from pathlib import Path
from typing import Dict, Optional

class ConfigManager:
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_dir(self) -> Path:
        """Get configuration directory following XDG spec"""
        xdg_config = os.getenv('XDG_CONFIG_HOME')
        if xdg_config:
            return Path(xdg_config) / 'ohc'
        return Path.home() / '.config' / 'ohc'

    def load_config(self) -> Dict:
        """Load configuration from file"""
        if not self.config_file.exists():
            return {"servers": {}, "default_server": None}

        with open(self.config_file, 'r') as f:
            return json.load(f)

    def save_config(self, config: Dict) -> None:
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(self.config_file, 0o600)  # Secure permissions
```

### 4.4 Server Commands

```python
# ohc/server_commands.py
import click
from .config import ConfigManager
from .api import OpenHandsAPI

@click.group()
def server():
    """Manage OpenHands server configurations."""
    pass

@server.command()
@click.option('--name', required=True, help='Server name')
@click.option('--url', required=True, help='Server API URL')
@click.option('--apikey', required=True, help='API key')
@click.option('--default', is_flag=True, help='Set as default server')
def add(name, url, apikey, default):
    """Add a new server configuration."""
    config_manager = ConfigManager()

    # Test connection
    click.echo(f"✓ Testing connection to {url}...")
    api = OpenHandsAPI(apikey, url)
    if not api.test_connection():
        click.echo("✗ Connection failed", err=True)
        raise click.Abort()

    # Save configuration
    config = config_manager.load_config()
    config['servers'][name] = {
        'url': url,
        'api_key': apikey,
        'default': default
    }

    if default:
        # Unset other defaults
        for server_config in config['servers'].values():
            server_config['default'] = False
        config['servers'][name]['default'] = True
        config['default_server'] = name

    config_manager.save_config(config)
    click.echo(f"✓ Server '{name}' added" + (" and set as default" if default else ""))
```

## 5. Implementation Plan

**General acceptance criteria:** All code must pass linting (flake8/black), include type hints, and have comprehensive error handling.

### 5.1 Foundation and Configuration Management (M1)

Create the basic CLI structure and configuration management system.

**Files to implement:**

- `ohc/__init__.py`
- `ohc/config.py`
- `ohc/cli.py` (basic structure)

**Acceptance criteria:**

- `ohc --version` and `ohc --help` work
- Configuration directory is created properly
- Config file format is established and tested

**Demo:** Basic CLI responds to version/help commands and creates config directory.

### 5.2 Server Management Commands (M2)

Implement server add/list/delete functionality with connection testing.

**Files to implement:**

- `ohc/server_commands.py`
- `ohc/api.py` (refactored from existing code)

**Acceptance criteria:**

- `ohc server add` works with all parameters and interactively
- `ohc server list` displays configured servers
- `ohc server delete` removes servers
- Connection testing validates API keys and URLs
- Default server management works correctly

**Demo:** User can add, list, and delete server configurations with connection validation.

### 5.3 Conversation Management Integration (M3)

Integrate existing conversation management functionality into the new CLI structure.

**Files to implement:**

- `ohc/conversation_commands.py`
- Update `ohc/cli.py` for interactive mode

**Acceptance criteria:**

- `ohc` (no args) starts interactive conversation manager
- `ohc -i` explicitly starts interactive mode
- `ohc conversations list` works with configured servers
- All existing conversation management features work

**Demo:** Full conversation management functionality available through new CLI structure.

### 5.4 Package Configuration and Migration (M4)

Update package configuration and provide migration path from old CLI.

**Files to implement:**

- Update `pyproject.toml`
- Migration documentation

**Acceptance criteria:**

- `ohc` command is available after installation
- Old `oh-conversation-manager`is removed
- Clear migration instructions provided
- Package metadata updated

**Demo:** Complete working CLI with both old and new entry points functional.
