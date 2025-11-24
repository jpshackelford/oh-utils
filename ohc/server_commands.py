"""
Server management commands for OpenHands Cloud CLI.

Handles adding, listing, deleting, and managing server configurations.
"""

import click

from .api import OpenHandsAPI
from .config import ConfigManager


@click.group()
def server() -> None:
    """Manage OpenHands server configurations."""
    pass


@server.command()
@click.option("--name", help="Server name")
@click.option("--url", help="Server API URL")
@click.option("--apikey", help="API key")
@click.option("--default", is_flag=True, help="Set as default server")
def add(name: str, url: str, apikey: str, default: bool) -> None:
    """Add a new server configuration."""
    config_manager = ConfigManager()

    # If any required parameters are missing, prompt for them
    if not name:
        name = click.prompt("Server name")

    if not url:
        url = click.prompt("Server URL", default="https://app.all-hands.dev/api/")

    if not apikey:
        apikey = click.prompt("API Key", hide_input=True)

    if not default and not click.get_current_context().params.get("default"):
        default = click.confirm("Set as default server?", default=False)

    # Ensure URL ends with /api/ if it doesn't already
    if not url.endswith("/api/") and not url.endswith("/api"):
        if url.endswith("/"):
            url += "api/"
        else:
            url += "/api/"

    # Test connection
    click.echo(f"Testing connection to {url}...")
    api = OpenHandsAPI(apikey, url)

    try:
        if not api.test_connection():
            click.echo("✗ Connection test failed - invalid URL or API key", err=True)
            if not click.confirm("Save server configuration anyway?"):
                raise click.Abort()
        else:
            # Additional test to ensure API key has proper permissions
            try:
                api.search_conversations(limit=1)
                click.echo("✓ Connection successful")
            except Exception as e:
                click.echo(
                    f"⚠ Connection partially successful but API key may have limited "
                    f"permissions: {e}"
                )
                if not click.confirm("Save server configuration anyway?"):
                    raise click.Abort() from None

    except Exception as e:
        click.echo(f"✗ Connection failed: {e}", err=True)
        if not click.confirm("Save server configuration anyway?"):
            raise click.Abort() from None

    # Check if server name already exists
    existing_servers = config_manager.list_servers()
    if (
        name in existing_servers
        and not click.confirm(f"Server '{name}' already exists. Overwrite?")
    ):
        click.echo("Operation cancelled.")
        return

    # Save configuration
    try:
        config_manager.add_server(name, url, apikey, default)
        success_msg = f"✓ Server '{name}' added"
        if default:
            success_msg += " and set as default"
        click.echo(success_msg)
    except Exception as e:
        click.echo(f"✗ Failed to save server configuration: {e}", err=True)
        raise click.Abort() from e


@server.command()
def list() -> None:
    """List all configured servers."""
    config_manager = ConfigManager()
    servers = config_manager.list_servers()

    if not servers:
        click.echo("No servers configured.")
        click.echo("Use 'ohc server add' to add a server.")
        return

    click.echo("Configured servers:")
    for name, config in servers.items():
        default_marker = "* " if config.get("default", False) else "  "
        url = config.get("url", "Unknown URL")
        default_text = " (default)" if config.get("default", False) else ""
        click.echo(f"{default_marker}{name:<15} {url}{default_text}")


@server.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def delete(name: str, force: bool) -> None:
    """Delete a server configuration."""
    config_manager = ConfigManager()

    # Check if server exists
    servers = config_manager.list_servers()
    if name not in servers:
        click.echo(f"✗ Server '{name}' not found.", err=True)
        return

    # Confirm deletion
    if not force and not click.confirm(f"Delete server '{name}'?"):
        click.echo("Operation cancelled.")
        return

    # Delete the server
    try:
        was_removed = config_manager.remove_server(name)
        if was_removed:
            click.echo(f"✓ Server '{name}' deleted")
        else:
            click.echo(f"✗ Failed to delete server '{name}'", err=True)
    except Exception as e:
        click.echo(f"✗ Failed to delete server: {e}", err=True)


@server.command("set-default")
@click.argument("name")
def set_default(name: str) -> None:
    """Set a server as the default."""
    config_manager = ConfigManager()

    # Check if server exists
    servers = config_manager.list_servers()
    if name not in servers:
        click.echo(f"✗ Server '{name}' not found.", err=True)
        return

    # Set as default
    try:
        success = config_manager.set_default_server(name)
        if success:
            click.echo(f"✓ Server '{name}' set as default")
        else:
            click.echo(f"✗ Failed to set server '{name}' as default", err=True)
    except Exception as e:
        click.echo(f"✗ Failed to set default server: {e}", err=True)


@server.command()
@click.argument("name", required=False)
def test(name: str) -> None:
    """Test connection to a server."""
    config_manager = ConfigManager()

    # Get server configuration
    if name:
        server_config = config_manager.get_server_config(name)
        if not server_config:
            click.echo(f"✗ Server '{name}' not found.", err=True)
            return
    else:
        server_config = config_manager.get_server_config()
        if not server_config:
            click.echo("✗ No servers configured.", err=True)
            return
        # Find the server name for display
        servers = config_manager.list_servers()
        name = next((n for n, c in servers.items() if c == server_config), "unknown")

    # Test connection
    click.echo(f"Testing connection to server '{name}'...")
    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    try:
        if not api.test_connection():
            click.echo("✗ Connection test failed - invalid URL or API key", err=True)
            return

        # Additional test to ensure API key has proper permissions
        api.search_conversations(limit=1)
        click.echo("✓ Connection successful")

    except Exception as e:
        click.echo(f"✗ Connection failed: {e}", err=True)
