"""
Conversation management commands for OpenHands Cloud CLI.

Integrates the existing conversation management functionality into the new CLI
structure.
"""

import os
import sys
from typing import Optional

import click

from .api import OpenHandsAPI
from .config import ConfigManager
from .conversation_display import show_conversation_details, show_workspace_changes


def _resolve_conversation_id(
    api: OpenHandsAPI, conversation_id_or_number: str
) -> Optional[str]:
    """Resolve conversation ID from number or partial ID."""
    try:
        # Try to parse as a number first
        conv_number = int(conversation_id_or_number)

        # Get the conversation list to find the conversation by number
        result = api.search_conversations(limit=100)
        conversations = result.get("results", [])

        if conv_number < 1 or conv_number > len(conversations):
            click.echo(
                f"✗ Conversation number {conv_number} is out of range "
                f"(1-{len(conversations)})",
                err=True,
            )
            return None

        conv_data = conversations[conv_number - 1]
        conversation_id = conv_data.get("conversation_id")
        return conversation_id if conversation_id else None

    except ValueError:
        # It's a conversation ID string - could be full or partial
        conv_id = conversation_id_or_number

        # If it's a short ID (8 chars or less), try to find a matching conversation
        if len(conv_id) <= 8:
            result = api.search_conversations(limit=100)
            conversations = result.get("results", [])

            matches = [
                c
                for c in conversations
                if c.get("conversation_id", "").startswith(conv_id)
            ]

            if not matches:
                click.echo(
                    f"✗ No conversation found with ID starting with '{conv_id}'",
                    err=True,
                )
                return None
            elif len(matches) > 1:
                click.echo(
                    f"✗ Multiple conversations match '{conv_id}'. "
                    f"Please use a longer ID:",
                    err=True,
                )
                for match in matches[:5]:  # Show first 5 matches
                    match_id = match.get("conversation_id", "")
                    match_title = match.get("title", "Untitled")[:40]
                    click.echo(f"  {match_id} - {match_title}")
                return None
            else:
                # Single match found
                conversation_id = matches[0].get("conversation_id")
                return conversation_id if conversation_id else None
        else:
            # Assume it's a full conversation ID
            return conv_id


@click.group()
def conv() -> None:
    """Manage OpenHands conversations."""
    pass


@conv.command()
@click.option("--server", help="Server name to use (defaults to configured default)")
@click.option(
    "-n",
    "--number",
    "limit",
    default=None,
    help="Number of conversations to list (default: all)",
)
def list(server: Optional[str], limit: Optional[int]) -> None:
    """List conversations."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)

    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo(
                "✗ No servers configured. Use 'ohc server add' to add a server.",
                err=True,
            )
        return

    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    try:
        # If no limit specified, get all conversations by using a large limit
        actual_limit = limit if limit is not None else 1000
        result = api.search_conversations(limit=actual_limit)
        conversations = result.get(
            "results", []
        )  # API returns 'results' not 'conversations'

        if not conversations:
            click.echo("No conversations found.")
            return

        click.echo(f"Found {len(conversations)} conversations:")
        for i, conv_data in enumerate(conversations, 1):
            conv_id = conv_data.get("conversation_id", "unknown")[:8]
            title = conv_data.get("title", "Untitled")
            status = conv_data.get("status", "UNKNOWN")

            # Truncate title if too long
            if len(title) > 50:
                title = title[:47] + "..."

            status_icon = (
                "🟢" if status == "RUNNING" else "🔴" if status == "STOPPED" else "🟡"
            )
            click.echo(f"{i:2d}. {conv_id} {status_icon} {status:8s} {title}")

    except Exception as e:
        click.echo(f"✗ Failed to list conversations: {e}", err=True)


def interactive_mode() -> None:
    """Start the interactive conversation manager."""
    # Import the original conversation manager and adapt it
    try:
        # Check if we have a configured server
        config_manager = ConfigManager()
        server_config = config_manager.get_server_config()

        if not server_config:
            click.echo("No servers configured.")
            click.echo("Use 'ohc server add' to add a server configuration.")

            # Offer to add a server interactively
            if click.confirm("Would you like to add a server now?"):
                from .server_commands import add

                ctx = click.Context(add)
                ctx.invoke(add)
                # Try to get server config again
                server_config = config_manager.get_server_config()
                if not server_config:
                    click.echo("No server configured. Exiting.")
                    return
            else:
                return

        # Set environment variable for the original conversation manager
        os.environ["OH_API_KEY"] = server_config["api_key"]

        # Import and run the original conversation manager
        from conversation_manager.conversation_manager import ConversationManager

        # Override the base URL in the API class if needed
        if server_config["url"] != "https://app.all-hands.dev/api/":
            # We need to patch the OpenHandsAPI class in the original module
            import conversation_manager.conversation_manager as cm

            original_init = cm.OpenHandsAPI.__init__

            def patched_init(self: object, api_key: str) -> None:
                original_init(self, api_key)  # type: ignore[arg-type]
                self.BASE_URL = server_config["url"]  # type: ignore[attr-defined]
                self.session.headers.update(  # type: ignore[attr-defined]
                    {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
                )

            cm.OpenHandsAPI.__init__ = patched_init  # type: ignore[method-assign]

        click.echo("Starting interactive conversation manager...")
        click.echo(f"Using server: {server_config['url']}")
        click.echo()

        manager = ConversationManager()
        manager.initialize()
        manager.run_interactive()

    except KeyboardInterrupt:
        click.echo("\nExiting...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Failed to start interactive mode: {e}", err=True)
        sys.exit(1)


@conv.command()
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
def wake(conversation_id_or_number: str, server: Optional[str]) -> None:
    """Wake up a conversation by ID (full or partial), or number from the list."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)

    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo(
                "✗ No servers configured. Use 'ohc server add' to add a server.",
                err=True,
            )
        return

    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    try:
        # Check if input is a number or a conversation ID
        try:
            conversation_number = int(conversation_id_or_number)
            # It's a number, so we need to get the list and find the conversation
            result = api.search_conversations(limit=100)
            conversations = result.get(
                "results", []
            )  # API returns 'results' not 'conversations'

            if conversation_number < 1 or conversation_number > len(conversations):
                click.echo(
                    f"✗ Invalid conversation number. Available: 1-{len(conversations)}",
                    err=True,
                )
                return

            conv_data = conversations[conversation_number - 1]
            conv_id = conv_data.get("conversation_id")
            title = conv_data.get("title", "Untitled")

        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number

            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get("results", [])

                matches = [
                    c
                    for c in conversations
                    if c.get("conversation_id", "").startswith(conv_id)
                ]

                if not matches:
                    click.echo(
                        f"✗ No conversation found with ID starting with '{conv_id}'",
                        err=True,
                    )
                    return
                elif len(matches) > 1:
                    click.echo(
                        f"✗ Multiple conversations match '${conv_id}'. "
                        f"Please use a longer ID:",
                        err=True,
                    )
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get("conversation_id", "")
                        match_title = match.get("title", "Untitled")[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get("conversation_id")
                    title = conv_data.get("title", "Untitled")
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."

        click.echo(f"Waking up conversation: {title}")

        result = api.start_conversation(conv_id)
        click.echo("✓ Conversation started successfully")

        if "url" in result:
            click.echo(f"URL: {result['url']}")

    except Exception as e:
        click.echo(f"✗ Failed to wake conversation: {e}", err=True)


@conv.command()
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
def show(conversation_id_or_number: str, server: Optional[str]) -> None:
    """Show detailed information about a conversation."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)

    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo(
                "✗ No servers configured. Use 'ohc server add' to add a server.",
                err=True,
            )
        return

    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    # Resolve conversation ID using shared logic
    conv_id = _resolve_conversation_id(api, conversation_id_or_number)
    if not conv_id:
        return

    # Use shared display functionality
    show_conversation_details(api, conv_id)


@conv.command(name="ws-download")
@click.argument("conversation_id_or_number")
@click.option(
    "-o",
    "--output",
    default=None,
    help="Output file path (default: conversation_id.zip)",
)
@click.option("--server", help="Server name to use (defaults to configured default)")
def ws_download(
    conversation_id_or_number: str, output: str, server: Optional[str]
) -> None:
    """Download workspace files as a ZIP archive."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)

    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo(
                "✗ No servers configured. Use 'ohc server add' to add a server.",
                err=True,
            )
        return

    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    try:
        # First, resolve the conversation ID using the same logic as other commands
        try:
            # Try to parse as a number first
            conv_number = int(conversation_id_or_number)

            # Get the conversation list to find the conversation by number
            result = api.search_conversations(limit=100)
            conversations = result.get("results", [])

            if conv_number < 1 or conv_number > len(conversations):
                click.echo(
                    f"✗ Conversation number {conv_number} is out of range "
                    f"(1-{len(conversations)})",
                    err=True,
                )
                return

            conv_data = conversations[conv_number - 1]
            conv_id = conv_data.get("conversation_id")
            title = conv_data.get("title", "Untitled")

        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number

            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get("results", [])

                matches = [
                    c
                    for c in conversations
                    if c.get("conversation_id", "").startswith(conv_id)
                ]

                if not matches:
                    click.echo(
                        f"✗ No conversation found with ID starting with '{conv_id}'",
                        err=True,
                    )
                    return
                elif len(matches) > 1:
                    click.echo(
                        f"✗ Multiple conversations match '${conv_id}'. "
                        f"Please use a longer ID:",
                        err=True,
                    )
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get("conversation_id", "")
                        match_title = match.get("title", "Untitled")[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get("conversation_id")
                    title = conv_data.get("title", "Untitled")
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."

        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        conversation_url = conv_details.get("url")
        session_api_key = conv_details.get("session_api_key")
        
        # Extract runtime base URL from conversation URL
        runtime_url = None
        if conversation_url:
            from urllib.parse import urlparse
            parsed = urlparse(conversation_url)
            runtime_url = f"{parsed.scheme}://{parsed.netloc}"

        click.echo(f"Downloading workspace for: {title}")

        # Download the workspace archive
        archive_data = api.download_workspace_archive(
            conv_id, runtime_url, session_api_key
        )

        # Determine output filename
        if not output:
            # Create a safe filename from conversation ID
            safe_id = conv_id[:8] if len(conv_id) >= 8 else conv_id
            output = f"{safe_id}.zip"

        # Write the archive to file
        with open(output, "wb") as f:
            f.write(archive_data)

        file_size = len(archive_data)
        size_mb = file_size / (1024 * 1024)
        click.echo(f"✓ Workspace downloaded successfully: {output} ({size_mb:.1f} MB)")

    except Exception as e:
        click.echo(f"✗ Failed to download workspace: {e}", err=True)


# Add alias for ws-download
@conv.command(name="ws-dl")
@click.argument("conversation_id_or_number")
@click.option(
    "-o",
    "--output",
    default=None,
    help="Output file path (default: conversation_id.zip)",
)
@click.option("--server", help="Server name to use (defaults to configured default)")
def ws_dl(conversation_id_or_number: str, output: str, server: Optional[str]) -> None:
    """Download workspace files as a ZIP archive (alias for ws-download)."""
    # Call the main ws-download function
    ctx = click.get_current_context()
    ctx.invoke(
        ws_download,
        conversation_id_or_number=conversation_id_or_number,
        output=output,
        server=server,
    )


@conv.command(name="ws-changes")
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
def ws_changes(conversation_id_or_number: str, server: Optional[str]) -> None:
    """Show workspace file changes (git status)."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)

    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo(
                "✗ No servers configured. Use 'ohc server add' to add a server.",
                err=True,
            )
        return

    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    # Resolve conversation ID using shared logic
    conv_id = _resolve_conversation_id(api, conversation_id_or_number)
    if not conv_id:
        return

    # Use shared display functionality
    show_workspace_changes(api, conv_id)


@conv.command()
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
def trajectory(
    conversation_id_or_number: str, server: Optional[str]
) -> None:
    """Download conversation trajectory as JSON file."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)

    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo(
                "✗ No servers configured. Use 'ohc server add' to add a server.",
                err=True,
            )
        return

    api = OpenHandsAPI(server_config["api_key"], server_config["url"])

    try:
        # First, resolve the conversation ID using the same logic as other commands
        try:
            # Try to parse as a number first
            conv_number = int(conversation_id_or_number)

            # Get the conversation list to find the conversation by number
            result = api.search_conversations(limit=100)
            conversations = result.get("results", [])

            if conv_number < 1 or conv_number > len(conversations):
                click.echo(
                    f"✗ Conversation number {conv_number} is out of range "
                    f"(1-{len(conversations)})",
                    err=True,
                )
                return

            conv_data = conversations[conv_number - 1]
            conv_id = conv_data.get("conversation_id")
            title = conv_data.get("title", "Untitled")

        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number

            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get("results", [])

                matches = [
                    c
                    for c in conversations
                    if c.get("conversation_id", "").startswith(conv_id)
                ]

                if not matches:
                    click.echo(
                        f"✗ No conversation found with ID starting with '{conv_id}'",
                        err=True,
                    )
                    return
                elif len(matches) > 1:
                    click.echo(
                        f"✗ Multiple conversations match '${conv_id}'. "
                        f"Please use a longer ID:",
                        err=True,
                    )
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get("conversation_id", "")
                        match_title = match.get("title", "Untitled")[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get("conversation_id")
                    title = conv_data.get("title", "Untitled")
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."

        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        full_url = conv_details.get("url")
        session_api_key = conv_details.get("session_api_key")

        if not full_url:
            click.echo(
                "✗ Conversation is not running. Trajectory is only available for "
                "active conversations.",
                err=True,
            )
            return

        if not session_api_key:
            click.echo(
                "✗ No session API key found for this conversation.",
                err=True,
            )
            return

        # Extract base runtime URL from the full conversation URL
        from urllib.parse import urlparse
        parsed_url = urlparse(full_url)
        runtime_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        click.echo(f"Trajectory for: {title}")

        # Get trajectory data
        trajectory_data = api.get_trajectory(conv_id, runtime_url, session_api_key)

        # Create JSON file with unique name
        import json
        from pathlib import Path
        
        base_name = f"trajectory-{conv_id[:8]}"
        json_path = Path(f"{base_name}.json")
        
        # Handle file name conflicts
        counter = 1
        while json_path.exists():
            json_path = Path(f"{base_name} ({counter}).json")
            counter += 1

        click.echo(f"💾 Creating trajectory file: {json_path.name}")

        # Write trajectory data to JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(trajectory_data, f, indent=2, ensure_ascii=False)

        click.echo(f"✅ Successfully created trajectory file: {json_path}")
        click.echo(f"📊 File size: {json_path.stat().st_size:,} bytes")

    except Exception as e:
        click.echo(f"✗ Failed to get trajectory: {e}", err=True)


# Add alias for trajectory
@conv.command()
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
def traj(conversation_id_or_number: str, server: Optional[str]) -> None:
    """Download conversation trajectory as JSON file - alias for trajectory."""
    # Call the main trajectory function
    ctx = click.get_current_context()
    ctx.invoke(
        trajectory,
        conversation_id_or_number=conversation_id_or_number,
        server=server,
    )
