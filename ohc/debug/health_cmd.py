"""Health command for cluster health overview."""

import json

import click

from ..k8s import RuntimeQuery
from ..k8s.client import K8sClientError
from .utils import get_config_and_client


def register_health_command(debug_group: click.Group) -> None:
    """Register the health command with the debug group."""

    @debug_group.command()
    @click.pass_context
    def health(ctx: click.Context) -> None:
        """Show cluster health overview."""
        env_config, app_client, runtime_client, env_name = get_config_and_client(
            ctx.obj.get("environment")
        )
        output = ctx.obj.get("output", "text")

        runtime_config = env_config.get_runtime_config()
        query = RuntimeQuery(runtime_client)
        health_summary = query.get_cluster_health(runtime_config.namespace)

        if output == "json":
            data = {
                "environment": env_name,
                "app_cluster": {
                    "context": env_config.app.kube_context,
                    "namespace": env_config.app.namespace,
                },
                "runtime_cluster": {
                    "context": runtime_config.kube_context,
                    "namespace": runtime_config.namespace,
                },
                "summary": {
                    "total_runtimes": health_summary.total_runtimes,
                    "running": health_summary.running_runtimes,
                    "pending": health_summary.pending_runtimes,
                    "error": health_summary.error_runtimes,
                    "oom_killed": health_summary.oom_killed_count,
                    "evicted": health_summary.evicted_count,
                    "failed_scheduling": health_summary.failed_scheduling_count,
                },
            }
            click.echo(json.dumps(data, indent=2))
            return

        click.echo()
        click.echo(f"OpenHands Environment: {env_name}")
        click.echo("=" * 40)
        click.echo()

        click.echo(f"App Cluster: {env_config.app.kube_context}")
        click.echo(f"  Namespace: {env_config.app.namespace}")

        # Check app cluster health
        try:
            deployments = app_client.list_deployments(env_config.app.namespace)
            total_deps = len(deployments)
            ready_deps = sum(
                1 for d in deployments if d["ready_replicas"] >= d["replicas"]
            )
            if ready_deps == total_deps:
                click.echo("  Status:    ✓ Healthy")
            else:
                click.echo("  Status:    ⚠ Issues detected")
            click.echo(f"  Deployments: {ready_deps}/{total_deps} ready")
        except K8sClientError as e:
            click.echo(f"  Status:    ✗ Error: {e}")

        click.echo()
        click.echo(f"Runtime Cluster: {runtime_config.kube_context}")
        click.echo(f"  Namespace: {runtime_config.namespace}")

        if health_summary.has_issues:
            click.echo("  Status:    ⚠ Issues detected")
        else:
            click.echo("  Status:    ✓ Healthy")

        click.echo()
        click.echo("Runtime Summary:")
        click.echo(f"  Total:      {health_summary.total_runtimes}")
        click.echo(
            f"  Running:    {health_summary.running_runtimes} "
            f"({health_summary.running_percentage:.0f}%)"
        )
        if health_summary.pending_runtimes > 0:
            click.echo(f"  Pending:    {health_summary.pending_runtimes}")
        if health_summary.error_runtimes > 0:
            click.echo(f"  Error:      {health_summary.error_runtimes} ⚠")

        has_oom = health_summary.oom_killed_count > 0
        has_sched = health_summary.failed_scheduling_count > 0
        if has_oom or has_sched:
            click.echo()
            click.echo("Resource Issues:")
            if health_summary.oom_killed_count > 0:
                click.echo(f"  OOMKilled:        {health_summary.oom_killed_count}")
            if health_summary.evicted_count > 0:
                click.echo(f"  Evicted:          {health_summary.evicted_count}")
            if health_summary.failed_scheduling_count > 0:
                click.echo(
                    f"  FailedScheduling: {health_summary.failed_scheduling_count}"
                )

        # Show top issues
        problem_pods = query.list_runtime_pods_with_issues(runtime_config.namespace)
        if problem_pods:
            click.echo()
            click.echo("Top Issues:")
            for pod in problem_pods[:5]:
                reasons = []
                if pod.is_oom_killed:
                    reasons.append("OOMKilled")
                if pod.restart_count > 0:
                    reasons.append(f"{pod.restart_count} restarts")
                reason_str = ", ".join(reasons) if reasons else pod.container_state
                click.echo(f"  {pod.runtime_id[:16]}  {reason_str}")

        click.echo()
