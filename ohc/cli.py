"""
Main CLI entry point for OpenHands Cloud (ohc).

Provides the multi-command CLI interface with server management and conversation
functionality.
"""

import click

from . import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ohc")
@click.option("-i", "--interactive", is_flag=True, help="Run in interactive mode")
@click.pass_context
def cli(ctx: click.Context, interactive: bool) -> None:
    """OpenHands Cloud CLI - Manage OpenHands servers and conversations."""
    ctx.ensure_object(dict)
    ctx.obj["interactive"] = interactive

    # If no subcommand provided
    if ctx.invoked_subcommand is None:
        if interactive:
            # Only start interactive mode if -i flag is used
            from .conversation_commands import interactive_mode

            interactive_mode()
        else:
            # Default behavior: show help
            click.echo(ctx.get_help())
            ctx.exit()


@click.command()
@click.pass_context
def help_command(ctx: click.Context) -> None:
    """Show help information."""
    # Get the parent context (the main cli group)
    parent_ctx = ctx.parent
    if parent_ctx:
        click.echo(parent_ctx.get_help())
    else:
        click.echo("No help available.")


def main() -> None:
    """Entry point for the ohc CLI."""
    # Import commands here to avoid circular imports
    from .conversation_commands import conv
    from .server_commands import server

    cli.add_command(server)
    cli.add_command(conv)
    cli.add_command(help_command, name="help")

    cli()


if __name__ == "__main__":
    main()
