"""Main debug command group for OpenHands Enterprise troubleshooting."""

import json
from typing import Any, Dict, Optional

import click

from ..debug_config import DebugConfigManager, EnvironmentConfig
from ..k8s import K8sClient, RuntimeDetector, RuntimeQuery
from ..k8s.client import K8sClientError
from ..k8s.detection import AppEndpointDetector
from ..k8s.queries import RuntimePod


def get_config_and_client(
    env: Optional[str] = None,
) -> tuple[EnvironmentConfig, K8sClient, K8sClient, str]:
    """
    Get environment config and K8s clients.

    Returns:
        Tuple of (env_config, app_client, runtime_client, env_name)

    Raises:
        click.ClickException if not configured
    """
    config_manager = DebugConfigManager()
    env_name = config_manager.get_environment_name(env)

    if not env_name:
        raise click.ClickException(
            "No debug environment configured. Run 'ohc debug configure' first."
        )

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        raise click.ClickException(f"Environment '{env_name}' not found.")

    try:
        app_client = K8sClient(env_config.app.kube_context)
        runtime_config = env_config.get_runtime_config()
        runtime_client = K8sClient(runtime_config.kube_context)
    except K8sClientError as e:
        raise click.ClickException(f"Failed to connect to Kubernetes: {e}") from e

    return env_config, app_client, runtime_client, env_name


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


@debug.command()
@click.option("--add", "add_name", help="Add a new environment with this name")
@click.option("--list", "list_envs", is_flag=True, help="List configured environments")
@click.option("--show", "show_env", is_flag=True, help="Show current configuration")
@click.option("--default", "set_default", help="Set default environment")
@click.option("--remove", "remove_name", help="Remove an environment")
@click.option("--test", "test_conn", is_flag=True, help="Test cluster connectivity")
@click.pass_context
def configure(
    ctx: click.Context,
    add_name: Optional[str],
    list_envs: bool,
    show_env: bool,
    set_default: Optional[str],
    remove_name: Optional[str],
    test_conn: bool,
) -> None:
    """Configure debug environments."""
    config_manager = DebugConfigManager()

    if list_envs:
        _list_environments(config_manager, ctx.obj.get("output", "text"))
        return

    if show_env:
        _show_configuration(config_manager, ctx.obj.get("output", "text"))
        return

    if set_default:
        if config_manager.set_default_environment(set_default):
            click.echo(f"✓ '{set_default}' set as default environment")
        else:
            raise click.ClickException(f"Environment '{set_default}' not found")
        return

    if remove_name:
        if config_manager.remove_environment(remove_name):
            click.echo(f"✓ Environment '{remove_name}' removed")
        else:
            raise click.ClickException(f"Environment '{remove_name}' not found")
        return

    if test_conn:
        _test_connectivity(config_manager)
        return

    # Interactive configuration
    _interactive_configure(config_manager, add_name)


def _list_environments(config_manager: DebugConfigManager, output: str) -> None:
    """List all configured environments."""
    envs = config_manager.list_environments()
    default_env = config_manager.get_default_environment_name()

    if not envs:
        click.echo("No environments configured. Run 'ohc debug configure' to add one.")
        return

    if output == "json":
        data = {
            "environments": envs,
            "default": default_env,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo("Configured environments:")
        for env in envs:
            marker = " (default)" if env == default_env else ""
            click.echo(f"  • {env}{marker}")


def _show_configuration(config_manager: DebugConfigManager, output: str) -> None:
    """Show current configuration."""
    config = config_manager.load_config()

    if output == "json":
        click.echo(json.dumps(config.to_dict(), indent=2))
        return

    if not config.environments:
        click.echo("No environments configured.")
        return

    click.echo("Debug Configuration")
    click.echo("=" * 40)
    click.echo(f"Default environment: {config.default_environment or 'none'}")
    click.echo()

    for name, env in config.environments.items():
        marker = " (default)" if name == config.default_environment else ""
        click.echo(f"Environment: {name}{marker}")
        click.echo("  App cluster:")
        click.echo(f"    Context:   {env.app.kube_context}")
        click.echo(f"    Namespace: {env.app.namespace}")
        runtime = env.get_runtime_config()
        click.echo("  Runtime cluster:")
        click.echo(f"    Context:   {runtime.kube_context}")
        click.echo(f"    Namespace: {runtime.namespace}")
        click.echo()


def _test_connectivity(config_manager: DebugConfigManager) -> None:
    """Test connectivity to configured clusters."""
    envs = config_manager.list_environments()

    if not envs:
        click.echo("No environments configured.")
        return

    click.echo("Testing cluster connectivity...")
    click.echo()

    for env_name in envs:
        env = config_manager.get_environment(env_name)
        if not env:
            continue

        click.echo(f"Environment: {env_name}")

        # Test app cluster
        try:
            app_client = K8sClient(env.app.kube_context)
            app_client.get_namespaces()
            click.echo(f"  ✓ App cluster ({env.app.kube_context}): connected")
        except K8sClientError as e:
            click.echo(f"  ✗ App cluster ({env.app.kube_context}): {e}")

        # Test runtime cluster
        runtime = env.get_runtime_config()
        try:
            runtime_client = K8sClient(runtime.kube_context)
            runtime_client.get_namespaces()
            click.echo(f"  ✓ Runtime cluster ({runtime.kube_context}): connected")
        except K8sClientError as e:
            click.echo(f"  ✗ Runtime cluster ({runtime.kube_context}): {e}")

        click.echo()


def _interactive_configure(
    config_manager: DebugConfigManager, env_name: Optional[str] = None
) -> None:
    """Run interactive configuration setup."""
    click.echo()
    click.echo("OpenHands Debug Tool - Configuration Setup")
    click.echo("=" * 42)
    click.echo()

    # Get environment name
    if not env_name:
        env_name = click.prompt("Environment name", default="production")

    # List available contexts
    contexts = K8sClient.list_contexts()
    if not contexts:
        raise click.ClickException(
            "No kubectl contexts found. Please configure kubectl first."
        )

    click.echo()
    click.echo("App Cluster (where OpenHands Enterprise Server runs)")
    click.echo("-" * 52)
    click.echo("Available kubectl contexts:")
    for i, ctx in enumerate(contexts, 1):
        active = " (active)" if ctx["active"] else ""
        click.echo(f"  {i}. {ctx['name']}{active}")

    click.echo()
    ctx_choice = click.prompt(
        f"Select app cluster context [1-{len(contexts)}]",
        type=click.IntRange(1, len(contexts)),
    )
    app_context = contexts[ctx_choice - 1]["name"]

    app_namespace = click.prompt("App namespace", default="openhands")

    # Auto-detect runtime configuration
    click.echo()
    click.echo("Detecting runtime configuration...")

    try:
        app_client = K8sClient(app_context)
        detector = RuntimeDetector(app_client)

        detected = detector.detect(app_namespace)
        if detected:
            click.echo("✓ Found runtime-api deployment")
            click.echo(f"✓ Detected: {detected.get_description()}")

            click.echo()
            click.echo("Runtime Cluster (where runtime pods run)")
            click.echo("-" * 40)

            if detected.same_cluster:
                runtime_context = app_context
                click.echo(f"  Context:   {runtime_context} (same as app)")
            else:
                # Try to match to available context
                matched = detector.match_context_to_detected(detected, contexts)
                if matched:
                    click.echo(f"✓ Found matching context: {matched}")
                    runtime_context = matched
                else:
                    click.echo("⚠ No matching kubectl context found")
                    click.echo()
                    for i, ctx in enumerate(contexts, 1):
                        click.echo(f"  {i}. {ctx['name']}")
                    ctx_choice = click.prompt(
                        f"Select runtime cluster context [1-{len(contexts)}]",
                        type=click.IntRange(1, len(contexts)),
                    )
                    runtime_context = contexts[ctx_choice - 1]["name"]

            runtime_namespace = detected.namespace
            click.echo(f"  Namespace: {runtime_namespace}")

            use_detected = click.confirm("Use detected settings?", default=True)
            if not use_detected:
                runtime_namespace = click.prompt(
                    "Runtime namespace", default=runtime_namespace
                )
        else:
            click.echo("⚠ Could not auto-detect runtime configuration")
            click.echo("  (runtime-api deployment not found)")
            click.echo()
            runtime_context = app_context
            runtime_namespace = click.prompt(
                "Runtime namespace", default="runtime-pods"
            )
    except K8sClientError as e:
        click.echo(f"⚠ Could not connect to cluster: {e}")
        runtime_context = app_context
        runtime_namespace = click.prompt("Runtime namespace", default="runtime-pods")

    # Detect application endpoint
    click.echo()
    click.echo("Detecting application endpoint...")

    app_url: Optional[str] = None
    try:
        endpoint_detector = AppEndpointDetector(app_client)
        endpoint = endpoint_detector.detect(app_namespace)
        if endpoint:
            click.echo(f"✓ Detected endpoint: {endpoint.url}")
            click.echo(f"  Source: {endpoint.source}")
            if click.confirm("Add this server to ohc?", default=True):
                app_url = endpoint.url
        else:
            click.echo("⚠ Could not auto-detect application endpoint")
            if click.confirm("Enter endpoint URL manually?", default=False):
                app_url = click.prompt(
                    "Application URL (e.g., https://openhands.example.com)"
                )
    except K8sClientError as e:
        click.echo(f"⚠ Could not detect endpoint: {e}")

    # Save configuration
    is_first = len(config_manager.list_environments()) == 0
    set_default = is_first or click.confirm(
        f"Set '{env_name}' as default environment?", default=True
    )

    config_manager.add_environment(
        name=env_name,
        app_context=app_context,
        app_namespace=app_namespace,
        runtime_context=runtime_context,
        runtime_namespace=runtime_namespace,
        set_default=set_default,
    )

    click.echo()
    click.echo(f"✓ Configuration saved to {config_manager.config_file}")
    if set_default:
        click.echo(f"✓ '{env_name}' set as default")

    # Add server if URL detected
    if app_url:
        click.echo()
        click.echo("Adding OpenHands server...")
        _add_server_from_url(env_name, app_url)

    click.echo()
    click.echo("Quick test:")
    click.echo("  ohc debug health")


def _add_server_from_url(env_name: str, app_url: str) -> None:
    """Add a server configuration from detected URL."""
    from ..config import ConfigManager

    config_manager = ConfigManager()

    # Ensure URL ends with /api/
    url = app_url
    if not url.endswith("/api/") and not url.endswith("/api"):
        if url.endswith("/"):
            url += "api/"
        else:
            url += "/api/"

    # Check if server already exists
    existing_servers = config_manager.list_servers()
    if env_name in existing_servers:
        click.echo(f"  Server '{env_name}' already exists, skipping")
        return

    # Prompt for API key
    click.echo(f"  Server URL: {url}")
    apikey = click.prompt("  API Key", hide_input=True, default="", show_default=False)

    if not apikey:
        click.echo("  Skipping server add (no API key provided)")
        click.echo(
            f"  You can add it later with: ohc server add --name {env_name} --url {url}"
        )
        return

    # Test connection
    click.echo("  Testing connection...")
    try:
        from ..api import create_api_client

        # Get API version from context if available
        ctx = click.get_current_context(silent=True)
        api_version = "v0"
        if ctx and ctx.obj:
            api_version = ctx.obj.get("api_version", "v0")

        api = create_api_client(apikey, url, api_version)
        if api.test_connection():
            click.echo("  ✓ Connection successful")
        else:
            click.echo("  ⚠ Connection test failed, but saving anyway")
    except Exception as e:
        click.echo(f"  ⚠ Connection test failed: {e}")
        if not click.confirm("  Save server configuration anyway?", default=True):
            click.echo(
                f"  You can add it later with: ohc server add "
                f"--name {env_name} --url {url}"
            )
            return

    # Save server
    config_manager.add_server(env_name, url, apikey, set_default=True)
    click.echo(f"  ✓ Server '{env_name}' added and set as default")


@debug.command()
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

    # Find the runtime pod
    pod = query.get_runtime_pod(runtime_id, runtime_config.namespace)

    if not pod:
        ns = runtime_config.namespace
        raise click.ClickException(
            f"Runtime '{runtime_id}' not found in namespace '{ns}'"
        )

    if output == "json":
        _output_runtime_json(pod, query, runtime_config.namespace, events or show_all)
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


@debug.command()
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
        ready_deps = sum(1 for d in deployments if d["ready_replicas"] >= d["replicas"])
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
            click.echo(f"  FailedScheduling: {health_summary.failed_scheduling_count}")

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


@debug.command("list")
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
    env_config, _app_client, runtime_client, _env_name = get_config_and_client(
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
        click.echo("No runtimes found matching criteria.")
        return

    # Table output
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


@debug.group()
def app() -> None:
    """App server commands."""
    pass


@app.command("logs")
@click.option("--follow", "-f", is_flag=True, help="Stream logs (not yet implemented)")
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
    env_config, app_client, runtime_client, env_name = get_config_and_client(
        ctx.obj.get("environment")
    )

    if follow:
        click.echo("⚠ --follow is not yet implemented")
        return

    # Parse since duration
    since_seconds = _parse_duration(since)

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
    env_config, app_client, runtime_client, env_name = get_config_and_client(
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
        click.echo(f"No deployments found in namespace '{env_config.app.namespace}'")
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
    env_config, app_client, runtime_client, env_name = get_config_and_client(
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


def _parse_duration(duration: str) -> int:
    """Parse duration string to seconds."""
    duration = duration.strip().lower()

    if duration.endswith("h"):
        return int(duration[:-1]) * 3600
    elif duration.endswith("m"):
        return int(duration[:-1]) * 60
    elif duration.endswith("s"):
        return int(duration[:-1])
    elif duration.endswith("d"):
        return int(duration[:-1]) * 86400
    else:
        return int(duration) * 60  # Default to minutes
