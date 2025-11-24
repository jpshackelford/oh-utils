"""
Conversation management commands for OpenHands Cloud CLI.

Integrates the existing conversation management functionality into the new CLI structure.
"""

import click
import sys
import os
from .config import ConfigManager
from .api import OpenHandsAPI


@click.group()
def conv():
    """Manage OpenHands conversations."""
    pass


@conv.command()
@click.option('--server', help='Server name to use (defaults to configured default)')
@click.option('-n', '--number', 'limit', default=None, help='Number of conversations to list (default: all)')
def list(server, limit):
    """List conversations."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)
    
    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo("✗ No servers configured. Use 'ohc server add' to add a server.", err=True)
        return
    
    api = OpenHandsAPI(server_config['api_key'], server_config['url'])
    
    try:
        # If no limit specified, get all conversations by using a large limit
        actual_limit = limit if limit is not None else 1000
        result = api.search_conversations(limit=actual_limit)
        conversations = result.get('results', [])  # API returns 'results' not 'conversations'
        
        if not conversations:
            click.echo("No conversations found.")
            return
        
        click.echo(f"Found {len(conversations)} conversations:")
        for i, conv_data in enumerate(conversations, 1):
            conv_id = conv_data.get('conversation_id', 'unknown')[:8]
            title = conv_data.get('title', 'Untitled')
            status = conv_data.get('status', 'UNKNOWN')
            
            # Truncate title if too long
            if len(title) > 50:
                title = title[:47] + "..."
            
            status_icon = "🟢" if status == 'RUNNING' else "🔴" if status == 'STOPPED' else "🟡"
            click.echo(f"{i:2d}. {conv_id} {status_icon} {status:8s} {title}")
            
    except Exception as e:
        click.echo(f"✗ Failed to list conversations: {e}", err=True)


def interactive_mode():
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
        os.environ['OH_API_KEY'] = server_config['api_key']
        
        # Import and run the original conversation manager
        from conversation_manager.conversation_manager import ConversationManager
        
        # Override the base URL in the API class if needed
        if server_config['url'] != "https://app.all-hands.dev/api/":
            # We need to patch the OpenHandsAPI class in the original module
            import conversation_manager.conversation_manager as cm
            original_init = cm.OpenHandsAPI.__init__
            
            def patched_init(self, api_key):
                original_init(self, api_key)
                self.BASE_URL = server_config['url']
                self.session.headers.update({
                    'X-Session-API-Key': api_key,
                    'Content-Type': 'application/json'
                })
            
            cm.OpenHandsAPI.__init__ = patched_init
        
        click.echo(f"Starting interactive conversation manager...")
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
@click.argument('conversation_id_or_number')
@click.option('--server', help='Server name to use (defaults to configured default)')
def wake(conversation_id_or_number, server):
    """Wake up a conversation by ID (full or partial), or number from the list."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)
    
    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo("✗ No servers configured. Use 'ohc server add' to add a server.", err=True)
        return
    
    api = OpenHandsAPI(server_config['api_key'], server_config['url'])
    
    try:
        # Check if input is a number or a conversation ID
        try:
            conversation_number = int(conversation_id_or_number)
            # It's a number, so we need to get the list and find the conversation
            result = api.search_conversations(limit=100)
            conversations = result.get('results', [])  # API returns 'results' not 'conversations'
            
            if conversation_number < 1 or conversation_number > len(conversations):
                click.echo(f"✗ Invalid conversation number. Available: 1-{len(conversations)}", err=True)
                return
            
            conv_data = conversations[conversation_number - 1]
            conv_id = conv_data.get('conversation_id')
            title = conv_data.get('title', 'Untitled')
            
        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number
            
            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get('results', [])
                
                matches = [c for c in conversations if c.get('conversation_id', '').startswith(conv_id)]
                
                if not matches:
                    click.echo(f"✗ No conversation found with ID starting with '{conv_id}'", err=True)
                    return
                elif len(matches) > 1:
                    click.echo(f"✗ Multiple conversations match '{conv_id}'. Please use a longer ID:", err=True)
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get('conversation_id', '')
                        match_title = match.get('title', 'Untitled')[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get('conversation_id')
                    title = conv_data.get('title', 'Untitled')
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."
        
        click.echo(f"Waking up conversation: {title}")
        
        result = api.start_conversation(conv_id)
        click.echo("✓ Conversation started successfully")
        
        if 'url' in result:
            click.echo(f"URL: {result['url']}")
            
    except Exception as e:
        click.echo(f"✗ Failed to wake conversation: {e}", err=True)


@conv.command()
@click.argument('conversation_id_or_number')
@click.option('--server', help='Server name to use (defaults to configured default)')
def show(conversation_id_or_number, server):
    """Show detailed information about a conversation."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)
    
    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo("✗ No servers configured. Use 'ohc server add' to add a server.", err=True)
        return
    
    api = OpenHandsAPI(server_config['api_key'], server_config['url'])
    
    try:
        # First, resolve the conversation ID using the same logic as wake command
        try:
            # Try to parse as a number first
            conv_number = int(conversation_id_or_number)
            
            # Get the conversation list to find the conversation by number
            result = api.search_conversations(limit=100)
            conversations = result.get('results', [])
            
            if conv_number < 1 or conv_number > len(conversations):
                click.echo(f"✗ Conversation number {conv_number} is out of range (1-{len(conversations)})", err=True)
                return
            
            conv_data = conversations[conv_number - 1]
            conv_id = conv_data.get('conversation_id')
            
        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number
            
            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get('results', [])
                
                matches = [c for c in conversations if c.get('conversation_id', '').startswith(conv_id)]
                
                if not matches:
                    click.echo(f"✗ No conversation found with ID starting with '{conv_id}'", err=True)
                    return
                elif len(matches) > 1:
                    click.echo(f"✗ Multiple conversations match '{conv_id}'. Please use a longer ID:", err=True)
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get('conversation_id', '')
                        match_title = match.get('title', 'Untitled')[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_id = matches[0].get('conversation_id')
        
        # Get detailed conversation information
        conv_details = api.get_conversation(conv_id)
        
        # Display conversation details
        click.echo(f"Conversation Details:")
        click.echo(f"  ID: {conv_details.get('conversation_id', 'N/A')}")
        click.echo(f"  Title: {conv_details.get('title', 'Untitled')}")
        click.echo(f"  Status: {conv_details.get('status', 'UNKNOWN')}")
        click.echo(f"  Created: {conv_details.get('created_at', 'N/A')}")
        click.echo(f"  Updated: {conv_details.get('updated_at', 'N/A')}")
        
        # Show runtime information if available
        runtime_id = conv_details.get('runtime_id')
        if runtime_id:
            click.echo(f"  Runtime ID: {runtime_id}")
            runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
            click.echo(f"  Runtime URL: {runtime_url}")
        
        # Show session API key if available
        session_api_key = conv_details.get('session_api_key')
        if session_api_key:
            click.echo(f"  Session API Key: {session_api_key[:8]}...")
        
        # Show additional metadata
        if 'metadata' in conv_details:
            metadata = conv_details['metadata']
            if metadata:
                click.echo(f"  Metadata:")
                for key, value in metadata.items():
                    click.echo(f"    {key}: {value}")
        
    except Exception as e:
        click.echo(f"✗ Failed to show conversation: {e}", err=True)


@conv.command(name='ws-download')
@click.argument('conversation_id_or_number')
@click.option('-o', '--output', default=None, help='Output file path (default: conversation_id.zip)')
@click.option('--server', help='Server name to use (defaults to configured default)')
def ws_download(conversation_id_or_number, output, server):
    """Download workspace files as a ZIP archive."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)
    
    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo("✗ No servers configured. Use 'ohc server add' to add a server.", err=True)
        return
    
    api = OpenHandsAPI(server_config['api_key'], server_config['url'])
    
    try:
        # First, resolve the conversation ID using the same logic as other commands
        try:
            # Try to parse as a number first
            conv_number = int(conversation_id_or_number)
            
            # Get the conversation list to find the conversation by number
            result = api.search_conversations(limit=100)
            conversations = result.get('results', [])
            
            if conv_number < 1 or conv_number > len(conversations):
                click.echo(f"✗ Conversation number {conv_number} is out of range (1-{len(conversations)})", err=True)
                return
            
            conv_data = conversations[conv_number - 1]
            conv_id = conv_data.get('conversation_id')
            title = conv_data.get('title', 'Untitled')
            
        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number
            
            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get('results', [])
                
                matches = [c for c in conversations if c.get('conversation_id', '').startswith(conv_id)]
                
                if not matches:
                    click.echo(f"✗ No conversation found with ID starting with '{conv_id}'", err=True)
                    return
                elif len(matches) > 1:
                    click.echo(f"✗ Multiple conversations match '{conv_id}'. Please use a longer ID:", err=True)
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get('conversation_id', '')
                        match_title = match.get('title', 'Untitled')[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get('conversation_id')
                    title = conv_data.get('title', 'Untitled')
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."
        
        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        runtime_id = conv_details.get('runtime_id')
        session_api_key = conv_details.get('session_api_key')
        
        click.echo(f"Downloading workspace for: {title}")
        
        # Download the workspace archive
        archive_data = api.download_workspace_archive(conv_id, runtime_id, session_api_key)
        
        # Determine output filename
        if not output:
            # Create a safe filename from conversation ID
            safe_id = conv_id[:8] if len(conv_id) >= 8 else conv_id
            output = f"{safe_id}.zip"
        
        # Write the archive to file
        with open(output, 'wb') as f:
            f.write(archive_data)
        
        file_size = len(archive_data)
        size_mb = file_size / (1024 * 1024)
        click.echo(f"✓ Workspace downloaded successfully: {output} ({size_mb:.1f} MB)")
        
    except Exception as e:
        click.echo(f"✗ Failed to download workspace: {e}", err=True)


# Add alias for ws-download
@conv.command(name='ws-dl')
@click.argument('conversation_id_or_number')
@click.option('-o', '--output', default=None, help='Output file path (default: conversation_id.zip)')
@click.option('--server', help='Server name to use (defaults to configured default)')
def ws_dl(conversation_id_or_number, output, server):
    """Download workspace files as a ZIP archive (alias for ws-download)."""
    # Call the main ws-download function
    ctx = click.get_current_context()
    ctx.invoke(ws_download, conversation_id_or_number=conversation_id_or_number, output=output, server=server)


@conv.command(name='ws-changes')
@click.argument('conversation_id_or_number')
@click.option('--server', help='Server name to use (defaults to configured default)')
def ws_changes(conversation_id_or_number, server):
    """Show workspace file changes (git status)."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)
    
    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo("✗ No servers configured. Use 'ohc server add' to add a server.", err=True)
        return
    
    api = OpenHandsAPI(server_config['api_key'], server_config['url'])
    
    try:
        # First, resolve the conversation ID using the same logic as other commands
        try:
            # Try to parse as a number first
            conv_number = int(conversation_id_or_number)
            
            # Get the conversation list to find the conversation by number
            result = api.search_conversations(limit=100)
            conversations = result.get('results', [])
            
            if conv_number < 1 or conv_number > len(conversations):
                click.echo(f"✗ Conversation number {conv_number} is out of range (1-{len(conversations)})", err=True)
                return
            
            conv_data = conversations[conv_number - 1]
            conv_id = conv_data.get('conversation_id')
            title = conv_data.get('title', 'Untitled')
            
        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number
            
            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get('results', [])
                
                matches = [c for c in conversations if c.get('conversation_id', '').startswith(conv_id)]
                
                if not matches:
                    click.echo(f"✗ No conversation found with ID starting with '{conv_id}'", err=True)
                    return
                elif len(matches) > 1:
                    click.echo(f"✗ Multiple conversations match '{conv_id}'. Please use a longer ID:", err=True)
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get('conversation_id', '')
                        match_title = match.get('title', 'Untitled')[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get('conversation_id')
                    title = conv_data.get('title', 'Untitled')
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."
        
        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        runtime_id = conv_details.get('runtime_id')
        session_api_key = conv_details.get('session_api_key')
        
        click.echo(f"Workspace changes for: {title}")
        
        # Get workspace changes
        changes = api.get_conversation_changes(conv_id, runtime_id, session_api_key)
        
        if not changes:
            click.echo("No changes found in workspace.")
            return
        
        # Group changes by status
        status_groups = {}
        for change in changes:
            status = change.get('status', 'unknown')
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(change.get('file_path', 'unknown'))
        
        # Display changes grouped by status
        status_icons = {
            'modified': '📝',
            'added': '➕',
            'deleted': '❌',
            'renamed': '🔄',
            'untracked': '❓'
        }
        
        for status, files in status_groups.items():
            icon = status_icons.get(status, '📄')
            click.echo(f"\n{icon} {status.upper()} ({len(files)} files):")
            for file_path in sorted(files):
                click.echo(f"  {file_path}")
        
    except Exception as e:
        click.echo(f"✗ Failed to get workspace changes: {e}", err=True)


@conv.command()
@click.argument('conversation_id_or_number')
@click.option('--server', help='Server name to use (defaults to configured default)')
@click.option('--limit', default=10, help='Number of recent trajectory events to show')
def trajectory(conversation_id_or_number, server, limit):
    """Show conversation trajectory (action history)."""
    config_manager = ConfigManager()
    server_config = config_manager.get_server_config(server)
    
    if not server_config:
        if server:
            click.echo(f"✗ Server '{server}' not found.", err=True)
        else:
            click.echo("✗ No servers configured. Use 'ohc server add' to add a server.", err=True)
        return
    
    api = OpenHandsAPI(server_config['api_key'], server_config['url'])
    
    try:
        # First, resolve the conversation ID using the same logic as other commands
        try:
            # Try to parse as a number first
            conv_number = int(conversation_id_or_number)
            
            # Get the conversation list to find the conversation by number
            result = api.search_conversations(limit=100)
            conversations = result.get('results', [])
            
            if conv_number < 1 or conv_number > len(conversations):
                click.echo(f"✗ Conversation number {conv_number} is out of range (1-{len(conversations)})", err=True)
                return
            
            conv_data = conversations[conv_number - 1]
            conv_id = conv_data.get('conversation_id')
            title = conv_data.get('title', 'Untitled')
            
        except ValueError:
            # It's a conversation ID string - could be full or partial
            conv_id = conversation_id_or_number
            
            # If it's a short ID (8 chars or less), try to find a matching conversation
            if len(conv_id) <= 8:
                result = api.search_conversations(limit=100)
                conversations = result.get('results', [])
                
                matches = [c for c in conversations if c.get('conversation_id', '').startswith(conv_id)]
                
                if not matches:
                    click.echo(f"✗ No conversation found with ID starting with '{conv_id}'", err=True)
                    return
                elif len(matches) > 1:
                    click.echo(f"✗ Multiple conversations match '{conv_id}'. Please use a longer ID:", err=True)
                    for match in matches[:5]:  # Show first 5 matches
                        match_id = match.get('conversation_id', '')
                        match_title = match.get('title', 'Untitled')[:40]
                        click.echo(f"  {match_id} - {match_title}")
                    return
                else:
                    # Single match found
                    conv_data = matches[0]
                    conv_id = conv_data.get('conversation_id')
                    title = conv_data.get('title', 'Untitled')
            else:
                # Full conversation ID
                title = f"Conversation {conv_id[:8]}..."
        
        # Get conversation details to check for runtime info
        conv_details = api.get_conversation(conv_id)
        runtime_id = conv_details.get('runtime_id')
        session_api_key = conv_details.get('session_api_key')
        
        if not runtime_id:
            click.echo(f"✗ Conversation is not running. Trajectory is only available for active conversations.", err=True)
            return
        
        click.echo(f"Trajectory for: {title}")
        
        # Get trajectory data
        trajectory_data = api.get_trajectory(conv_id, runtime_id, session_api_key)
        
        # Extract events from trajectory
        events = trajectory_data.get('events', [])
        if not events:
            click.echo("No trajectory events found.")
            return
        
        # Show the most recent events (limited by --limit)
        recent_events = events[-limit:] if len(events) > limit else events
        
        click.echo(f"\nShowing {len(recent_events)} most recent events:")
        click.echo("-" * 60)
        
        for i, event in enumerate(recent_events, 1):
            event_type = event.get('type', 'unknown')
            timestamp = event.get('timestamp', 'N/A')
            source = event.get('source', 'unknown')
            
            # Format timestamp if available
            if timestamp and timestamp != 'N/A':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%H:%M:%S')
                except:
                    formatted_time = timestamp
            else:
                formatted_time = 'N/A'
            
            click.echo(f"{i:2d}. [{formatted_time}] {event_type} ({source})")
            
            # Show event content/message if available
            content = event.get('content') or event.get('message') or event.get('text')
            if content:
                # Truncate long content
                if len(content) > 100:
                    content = content[:97] + "..."
                click.echo(f"    {content}")
            
            # Show additional relevant fields
            if 'tool' in event:
                click.echo(f"    Tool: {event['tool']}")
            if 'action' in event:
                click.echo(f"    Action: {event['action']}")
            
            click.echo()  # Empty line between events
        
        total_events = len(events)
        if total_events > limit:
            click.echo(f"... and {total_events - limit} more events (use --limit to see more)")
        
    except Exception as e:
        click.echo(f"✗ Failed to get trajectory: {e}", err=True)


# Add alias for trajectory
@conv.command()
@click.argument('conversation_id_or_number')
@click.option('--server', help='Server name to use (defaults to configured default)')
@click.option('--limit', default=10, help='Number of recent trajectory events to show')
def traj(conversation_id_or_number, server, limit):
    """Show conversation trajectory (action history) - alias for trajectory."""
    # Call the main trajectory function
    ctx = click.get_current_context()
    ctx.invoke(trajectory, conversation_id_or_number=conversation_id_or_number, server=server, limit=limit)