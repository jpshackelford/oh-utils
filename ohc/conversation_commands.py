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
@click.option('--limit', default=20, help='Number of conversations to list')
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
        result = api.search_conversations(limit=limit)
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