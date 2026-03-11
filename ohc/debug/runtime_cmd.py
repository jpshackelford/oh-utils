"""Runtime command for investigating specific runtime pods."""

import json
from typing import Any, Dict

import click

from ..k8s import RuntimeQuery
from ..k8s.client import K8sClientError
from ..k8s.queries import RuntimePod
from .utils import get_config_and_client


def register_runtime_command(debug_group: click.Group) -> None:
    """Register the runtime command with the debug group."""

    @debug_group.command()
    @click.argument("runtime_id")
    @click.option("--events", is_flag=True, help="Show full event history")
    @click.option("--logs", is_flag=True, help="Show container logs")
    @click.option("--previous", is_flag=True, help="Show logs from previous container")
    @click.option("--all", "show_all", is_flag=True, help="Show everything")
    @click.pass_context
    def runtime(
        ctx: click.Context,
        runtime_id: str,
        events: bool,
        logs: bool,
        previous: bool,
        show_all: bool,
    ) -> None:
        """Investigate a specific runtime.

        RUNTIME_ID can be the runtime ID, session ID, or pod name.
        """
        env_config, _app_client, runtime_client, _env_name = get_config_and_client(
            ctx.obj.get("environment")
        )
        output = ctx.obj.get("output", "text")

        runtime_config = env_config.get_runtime_config()
        query = RuntimeQuery(runtime_client)
        ns = runtime_config.namespace

        # Find the runtime pod
        pod = query.get_runtime_pod(runtime_id, ns)

        if not pod:
            # Check if there are multiple matches (ambiguous prefix)
            matches = query.find_runtime_pods(runtime_id, ns)
            if len(matches) > 1:
                ids = ", ".join(p.runtime_id for p in matches[:5])
                if len(matches) > 5:
                    ids += f", ... ({len(matches)} total)"
                raise click.ClickException(
                    f"Ambiguous runtime ID '{runtime_id}' matches multiple "
                    f"runtimes: {ids}\nPlease provide a more specific ID."
                )
            raise click.ClickException(
                f"Runtime '{runtime_id}' not found in namespace '{ns}'"
            )

        if output == "json":
            _output_runtime_json(
                pod, query, runtime_config.namespace, events or show_all
            )
            return

        # Display runtime info
        click.echo()
        click.echo(f"Runtime: {pod.runtime_id}")
        if pod.session_id:
            click.echo(f"Session: {pod.session_id}")
        click.echo(f"Status:  {pod.status_display()}")
        click.echo(f"Pod:     {pod.name}")
        if pod.created_at:
            click.echo(f"Created: {pod.created_at} ({pod.age_display} ago)")
        else:
            click.echo("Created: unknown")
        click.echo()

        click.echo("Resources:")
        cpu_req = pod.cpu_request or "N/A"
        cpu_lim = pod.cpu_limit or "N/A"
        mem_req = pod.memory_request or "N/A"
        mem_lim = pod.memory_limit or "N/A"
        click.echo(f"  CPU:    {cpu_req} requested / {cpu_lim} limit")
        click.echo(f"  Memory: {mem_req} requested / {mem_lim} limit")

        if pod.restart_count > 0:
            click.echo()
            click.echo("Pod Status:")
            click.echo(f"  Restarts: {pod.restart_count}")
            if pod.last_restart_reason:
                click.echo(f"  Last Restart Reason: {pod.last_restart_reason}")

        # Show events
        if events or show_all:
            click.echo()
            click.echo("Events:")
            pod_events = query.get_pod_events(pod.name, runtime_config.namespace)
            if pod_events:
                for event in pod_events[:10]:
                    last_ts = event.get("last_timestamp")
                    timestamp = last_ts[:19] if last_ts else ""
                    etype = event.get("type", "")
                    reason = event.get("reason", "")
                    message = event.get("message", "")
                    icon = "⚠️" if etype == "Warning" else "ℹ️"
                    click.echo(f"  {timestamp} {icon} {reason}: {message}")
            else:
                click.echo("  No events found")

        # Show logs
        if logs or show_all:
            click.echo()
            click.echo("Logs:" if not previous else "Previous Logs:")
            try:
                log_output = runtime_client.get_pod_logs(
                    pod.name, runtime_config.namespace, previous=previous, tail_lines=50
                )
                if log_output:
                    for line in log_output.strip().split("\n")[-20:]:
                        click.echo(f"  {line}")
                else:
                    click.echo("  No logs available")
            except K8sClientError as e:
                click.echo(f"  Could not fetch logs: {e}")

        # Show recommendation if there are issues
        if pod.is_oom_killed:
            click.echo()
            click.echo("💡 Recommendation: This runtime was OOMKilled.")
            click.echo("   Consider increasing resource_factor for this user's org.")

        click.echo()


def _output_runtime_json(
    pod: RuntimePod,
    query: RuntimeQuery,
    namespace: str,
    include_events: bool,
) -> None:
    """Output runtime info as JSON."""
    data: Dict[str, Any] = {
        "runtime_id": pod.runtime_id,
        "session_id": pod.session_id,
        "pod_name": pod.name,
        "status": pod.phase,
        "container_state": pod.container_state,
        "restarts": pod.restart_count,
        "last_restart_reason": pod.last_restart_reason,
        "resources": {
            "cpu_request": pod.cpu_request,
            "cpu_limit": pod.cpu_limit,
            "memory_request": pod.memory_request,
            "memory_limit": pod.memory_limit,
        },
        "created_at": pod.created_at.isoformat() if pod.created_at else None,
        "node_name": pod.node_name,
    }

    if include_events:
        events = query.get_pod_events(pod.name, namespace)
        data["events"] = events

    click.echo(json.dumps(data, indent=2, default=str))
