"""Main debug command group for OpenHands Enterprise troubleshooting.

This module provides the main `debug` command group and registers all subcommands
from their respective modules:
- configure_cmd: Environment configuration
- runtime_cmd: Runtime investigation
- health_cmd: Cluster health overview
- list_cmd: Runtime listing with filters
- app_cmd: App server diagnostics
"""

from typing import Optional

import click

from .app_cmd import register_app_commands
from .configure_cmd import register_configure_command
from .health_cmd import register_health_command
from .list_cmd import register_list_command
from .runtime_cmd import register_runtime_command


@click.group()
@click.option(
    "-e",
    "--env",
    "environment",
    help="Use specific environment (default: use configured default)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "table"]),
    default="text",
    help="Output format",
)
@click.pass_context
def debug(ctx: click.Context, environment: Optional[str], output: str) -> None:
    """Debug OpenHands Enterprise deployments.

    Troubleshoot runtime issues, view logs, and check cluster health.
    """
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["output"] = output


# Register all subcommands
register_configure_command(debug)
register_runtime_command(debug)
register_health_command(debug)
register_list_command(debug)
register_app_commands(debug)
