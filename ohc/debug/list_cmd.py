"""List command for listing runtime pods with filters."""

import json

import click

from ..k8s import RuntimeQuery
from .utils import get_config_and_client


def register_list_command(debug_group: click.Group) -> None:
    """Register the list command with the debug group."""

    @debug_group.command("list")
    @click.option("--errors", is_flag=True, help="Show only runtimes with errors")
    @click.option("--restarts", is_flag=True, help="Show runtimes with restarts")
    @click.option("--min", "min_restarts", type=int, default=1, help="Min restarts")
    @click.option("--oom", is_flag=True, help="Show OOMKilled runtimes")
    @click.option("--recent", is_flag=True, help="Show recently created (last 1h)")
    @click.pass_context
    def list_runtimes(
        ctx: click.Context,
        errors: bool,
        restarts: bool,
        min_restarts: int,
        oom: bool,
        recent: bool,
    ) -> None:
        """List runtime pods with optional filters."""
        env_config, _app_client, runtime_client, env_name = get_config_and_client(
            ctx.obj.get("environment")
        )
        output = ctx.obj.get("output", "text")

        runtime_config = env_config.get_runtime_config()
        query = RuntimeQuery(runtime_client)
        ns = runtime_config.namespace

        # Get pods based on filters
        if oom:
            pods = query.list_oom_killed_runtimes(ns)
        elif restarts:
            pods = query.list_runtimes_with_restarts(ns, min_restarts)
        elif errors:
            pods = query.list_runtime_pods_with_issues(ns)
        else:
            pods = query.list_runtime_pods(ns)

        # Filter recent if requested
        if recent:
            from datetime import datetime, timedelta, timezone

            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            pods = [p for p in pods if p.created_at and p.created_at > cutoff]

        if output == "json":
            data = [
                {
                    "runtime_id": p.runtime_id,
                    "session_id": p.session_id,
                    "status": p.phase,
                    "restarts": p.restart_count,
                    "restart_reason": p.last_restart_reason,
                    "age": p.age_display,
                }
                for p in pods
            ]
            click.echo(json.dumps(data, indent=2))
            return

        if not pods:
            click.echo(f"No runtimes found matching criteria in {env_name}.")
            return

        # Table output - show environment header
        click.echo()
        click.echo(f"Environment: {env_name} (namespace: {ns})")
        click.echo()
        header = f"{'RUNTIME ID':<20} {'STATUS':<15} {'RESTARTS':<10} {'REASON':<10}"
        click.echo(header)
        click.echo("-" * 60)

        for pod in pods:
            rid = pod.runtime_id[:18] if len(pod.runtime_id) > 18 else pod.runtime_id
            st = pod.container_state[:13] if pod.container_state else pod.phase[:13]
            rsn = (pod.last_restart_reason or "-")[:8]
            click.echo(f"{rid:<20} {st:<15} {pod.restart_count:<10} {rsn:<10}")

        click.echo()
        click.echo(f"{len(pods)} runtime(s) found")
