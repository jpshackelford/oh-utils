"""
Main CLI entry point for OpenHands Cloud (ohc).

Provides the multi-command CLI interface with server management and conversation functionality.
"""

import click
from . import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name='ohc')
@click.option('-i', '--interactive', is_flag=True, help='Run in interactive mode')
@click.pass_context
def cli(ctx, interactive):
    """OpenHands Cloud CLI - Manage OpenHands servers and conversations."""
    ctx.ensure_object(dict)
    ctx.obj['interactive'] = interactive
    
    # If no subcommand provided, start interactive conversation manager
    if ctx.invoked_subcommand is None:
        from .conversation_commands import interactive_mode
        interactive_mode()


def main():
    """Entry point for the ohc CLI."""
    # Import commands here to avoid circular imports
    from .server_commands import server
    from .conversation_commands import conversations
    
    cli.add_command(server)
    cli.add_command(conversations)
    
    cli()


if __name__ == '__main__':
    main()