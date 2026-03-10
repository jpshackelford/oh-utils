"""App command group for app server diagnostics."""

import json
from typing import Optional

import click

from ..k8s.client import K8sClientError
from .utils import get_config_and_client, parse_duration


def register_app_commands(debug_group: click.Group) -> None:
    """Register the app command group with the debug group."""

    @debug_group.group()
    def app() -> None:
        """App server commands."""
        pass

    @app.command("logs")
    @click.option(
        "--follow", "-f", is_flag=True, help="Stream logs (not yet implemented)"
    )
    @click.option("--since", default="1h", help="Show logs since (e.g., 1h, 30m)")
    @click.option("--component", help="Specific component (e.g., api, runtime-api)")
    @click.option("--tail", type=int, default=100, help="Number of lines to show")
    @click.pass_context
    def app_logs(
        ctx: click.Context,
        follow: bool,
        since: str,
        component: Optional[str],
        tail: int,
    ) -> None:
        """Show app server logs."""
        env_config, app_client, _runtime_client, _env_name = get_config_and_client(
            ctx.obj.get("environment")
        )

        if follow:
            click.echo("⚠ --follow is not yet implemented")
            return

        # Parse since duration
        since_seconds = parse_duration(since)

        # Find app pods
        try:
            pods = app_client.list_pods(env_config.app.namespace)
        except K8sClientError as e:
            raise click.ClickException(f"Failed to list pods: {e}") from e

        if component:
            pods = [p for p in pods if component.lower() in p["name"].lower()]

        if not pods:
            click.echo(f"No pods found in namespace '{env_config.app.namespace}'")
            return

        for pod in pods[:3]:  # Limit to first 3 pods
            click.echo()
            click.echo(f"=== {pod['name']} ===")
            try:
                logs = app_client.get_pod_logs(
                    pod["name"],
                    env_config.app.namespace,
                    tail_lines=tail,
                    since_seconds=since_seconds,
                )
                if logs:
                    click.echo(logs)
                else:
                    click.echo("(no logs)")
            except K8sClientError as e:
                click.echo(f"Error: {e}")

    @app.command("status")
    @click.pass_context
    def app_status(ctx: click.Context) -> None:
        """Show app server deployment status."""
        env_config, app_client, _runtime_client, _env_name = get_config_and_client(
            ctx.obj.get("environment")
        )
        output = ctx.obj.get("output", "text")

        try:
            deployments = app_client.list_deployments(env_config.app.namespace)
        except K8sClientError as e:
            raise click.ClickException(f"Failed to list deployments: {e}") from e

        if output == "json":
            click.echo(json.dumps(deployments, indent=2))
            return

        if not deployments:
            click.echo(
                f"No deployments found in namespace '{env_config.app.namespace}'"
            )
            return

        click.echo()
        click.echo(f"{'DEPLOYMENT':<30} {'READY':<10} {'AVAILABLE':<10}")
        click.echo("-" * 55)

        for dep in deployments:
            name = dep["name"][:28] if len(dep["name"]) > 28 else dep["name"]
            ready = f"{dep['ready_replicas']}/{dep['replicas']}"
            available = dep["available_replicas"]
            click.echo(f"{name:<30} {ready:<10} {available:<10}")

        click.echo()

    @app.command("pods")
    @click.pass_context
    def app_pods(ctx: click.Context) -> None:
        """List app server pods."""
        env_config, app_client, _runtime_client, _env_name = get_config_and_client(
            ctx.obj.get("environment")
        )
        output = ctx.obj.get("output", "text")

        try:
            pods = app_client.list_pods(env_config.app.namespace)
        except K8sClientError as e:
            raise click.ClickException(f"Failed to list pods: {e}") from e

        if output == "json":
            click.echo(json.dumps(pods, indent=2, default=str))
            return

        if not pods:
            click.echo(f"No pods found in namespace '{env_config.app.namespace}'")
            return

        click.echo()
        click.echo(f"{'POD':<40} {'STATUS':<12} {'NODE':<20}")
        click.echo("-" * 75)

        for pod in pods:
            name = pod["name"][:38] if len(pod["name"]) > 38 else pod["name"]
            status = pod.get("phase", "Unknown")
            node = (pod.get("node_name") or "")[:18]
            click.echo(f"{name:<40} {status:<12} {node:<20}")

        click.echo()
