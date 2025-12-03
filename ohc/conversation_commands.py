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
from .command_utils import resolve_conversation_id, with_server_config
from .config import ConfigManager
from .conversation_display import show_conversation_details, show_workspace_changes


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
@with_server_config
def list(api: OpenHandsAPI, server: Optional[str], limit: Optional[int]) -> None:  # noqa: ARG001
    """List conversations."""
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
            # Use the Conversation class to handle both v0 and v1 formats
            from .conversation_display import Conversation
            conv = Conversation.from_api_response(conv_data)
            
            # Format version indicator if available
            version_indicator = ""
            if conv.version:
                version_indicator = f" [{conv.version}]"
            
            click.echo(f"{i:2d}. {conv.short_id()} {conv.status_display():12s} {conv.formatted_title()}{version_indicator}")

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

            def patched_init(self: object, api_key: str, **_kwargs: object) -> None:
                # Accept **kwargs to be compatible with both old and new signatures
                # Ignore base_url if provided since we're setting BASE_URL directly
                original_init(self, api_key)  # type: ignore[arg-type]
                self.BASE_URL = server_config["url"]  # type: ignore[attr-defined]
                self.session.headers.update(  # type: ignore[attr-defined]
                    {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
                )

            cm.OpenHandsAPI.__init__ = patched_init  # type: ignore[assignment,method-assign]

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
@with_server_config
def wake(
    api: OpenHandsAPI,
    conversation_id_or_number: str,
    server: Optional[str],  # noqa: ARG001
) -> None:
    """Wake up a conversation by ID (full or partial), or number from the list."""
    try:
        # Resolve conversation ID using shared logic
        conv_id = resolve_conversation_id(api, conversation_id_or_number)
        if not conv_id:
            return

        # Get conversation details for title
        conv_details = api.get_conversation(conv_id)
        if conv_details:
            title = conv_details.get("title", f"Conversation {conv_id[:8]}...")
        else:
            title = f"Conversation {conv_id[:8]}..."

        click.echo(f"Waking up conversation: {title}")

        result = api.start_conversation({"conversation_id": conv_id})
        click.echo("✓ Conversation started successfully")

        if "url" in result:
            click.echo(f"URL: {result['url']}")

    except Exception as e:
        click.echo(f"✗ Failed to wake conversation: {e}", err=True)


@conv.command()
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
@with_server_config
def show(
    api: OpenHandsAPI,
    conversation_id_or_number: str,
    server: Optional[str],  # noqa: ARG001
) -> None:
    """Show detailed information about a conversation."""
    # Resolve conversation ID using shared logic
    conv_id = resolve_conversation_id(api, conversation_id_or_number)
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
@with_server_config
def ws_download(
    api: OpenHandsAPI,
    conversation_id_or_number: str,
    output: str,
    server: Optional[str],  # noqa: ARG001
) -> None:
    """Download workspace files as a ZIP archive."""
    try:
        # Resolve conversation ID using shared logic
        conv_id = resolve_conversation_id(api, conversation_id_or_number)
        if not conv_id:
            return

        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        if not conv_details:
            click.echo(f"✗ Conversation {conv_id} not found", err=True)
            return
        conversation_url = conv_details.get("url")
        session_api_key = conv_details.get("session_api_key")
        title = conv_details.get("title", f"Conversation {conv_id[:8]}...")

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

        if archive_data is None:
            click.echo("✗ Failed to download workspace archive", err=True)
            return

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
@with_server_config
def ws_changes(
    api: OpenHandsAPI,
    conversation_id_or_number: str,
    server: Optional[str],  # noqa: ARG001
) -> None:
    """Show workspace file changes (git status)."""
    # Resolve conversation ID using shared logic
    conv_id = resolve_conversation_id(api, conversation_id_or_number)
    if not conv_id:
        return

    # Use shared display functionality
    show_workspace_changes(api, conv_id)


@conv.command()
@click.argument("conversation_id_or_number")
@click.option("--server", help="Server name to use (defaults to configured default)")
@with_server_config
def trajectory(
    api: OpenHandsAPI,
    conversation_id_or_number: str,
    server: Optional[str],  # noqa: ARG001
) -> None:
    """Download conversation trajectory as JSON file."""
    try:
        # Resolve conversation ID using shared logic
        conv_id = resolve_conversation_id(api, conversation_id_or_number)
        if not conv_id:
            return

        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        if not conv_details:
            click.echo(f"✗ Conversation {conv_id} not found", err=True)
            return
        full_url = conv_details.get("url")
        session_api_key = conv_details.get("session_api_key")
        title = conv_details.get("title", f"Conversation {conv_id[:8]}...")

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


@conv.command()
@click.option("--server", help="Server name to use (defaults to configured default)")
@click.option(
    "--start/--no-start",
    default=True,
    help="Start the conversation immediately (default: True)",
)
@click.option(
    "--providers",
    default="github",
    help="Comma-separated list of providers to use (default: github)",
)
@click.argument("prompt", required=False)
@with_server_config
def new(
    api: OpenHandsAPI,
    server: Optional[str],  # noqa: ARG001
    start: bool,
    providers: str,
    prompt: Optional[str],
) -> None:
    """Create a new conversation with an optional prompt.
    
    PROMPT can be provided as an argument, piped from stdin, or entered interactively.
    
    Examples:
        ohc conv new "Help me write a Python script"
        echo "Create a web app" | ohc conv new
        ohc conv new  # Interactive prompt entry
    """
    try:
        # Get the prompt from various sources
        final_prompt = _get_prompt_from_sources(prompt)
        
        # Create the conversation
        click.echo("Creating new conversation...")
        result = api.create_conversation()
        
        if result.get("status") != "ok":
            click.echo(f"✗ Failed to create conversation: {result}", err=True)
            return
            
        conversation_id = result.get("conversation_id")
        if not conversation_id:
            click.echo("✗ No conversation ID returned from API", err=True)
            return
            
        click.echo(f"✓ Created conversation: {conversation_id[:8]}...")
        
        # Start the conversation if requested
        if start:
            click.echo("Starting conversation...")
            providers_list = [p.strip() for p in providers.split(",")]
            start_result = api.start_conversation({"conversation_id": conversation_id})
            
            if start_result.get("status") == "ok":
                click.echo("✓ Conversation started successfully")
                
                # Get the conversation details to show the URL
                conv_details = api.get_conversation(conversation_id)
                if conv_details and conv_details.get("url"):
                    click.echo(f"🌐 Conversation URL: {conv_details['url']}")
                    
                    # If we have a prompt, show instructions for using it
                    if final_prompt:
                        click.echo()
                        click.echo("📝 Your prompt:")
                        click.echo(f"   {final_prompt}")
                        click.echo()
                        click.echo("💡 Copy and paste this prompt into the conversation to get started!")
                else:
                    click.echo("⚠️  Conversation started but no URL available yet")
            else:
                click.echo(f"✗ Failed to start conversation: {start_result}", err=True)
        else:
            click.echo(f"💤 Conversation created but not started (use --start to start immediately)")
            click.echo(f"   Use 'ohc conv wake {conversation_id[:8]}' to start it later")
            
        # Show the prompt if we have one but didn't start
        if final_prompt and not start:
            click.echo()
            click.echo("📝 Your prompt (saved for when you start the conversation):")
            click.echo(f"   {final_prompt}")
            
    except Exception as e:
        click.echo(f"✗ Failed to create conversation: {e}", err=True)


def _get_prompt_from_sources(prompt_arg: Optional[str]) -> Optional[str]:
    """Get prompt from argument, stdin, or interactive input."""
    # 1. Use argument if provided
    if prompt_arg:
        return prompt_arg.strip()
    
    # 2. Check if there's piped input
    if not sys.stdin.isatty():
        piped_input = sys.stdin.read().strip()
        if piped_input:
            return piped_input
    
    # 3. Interactive input
    try:
        click.echo("Enter your prompt (press Enter twice to finish, Ctrl+C to skip):")
        lines = []
        empty_line_count = 0
        
        while True:
            try:
                line = input()
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                    lines.append(line)
                else:
                    empty_line_count = 0
                    lines.append(line)
            except EOFError:
                break
                
        prompt = "\n".join(lines).strip()
        return prompt if prompt else None
        
    except KeyboardInterrupt:
        click.echo("\nSkipping prompt entry...")
        return None
