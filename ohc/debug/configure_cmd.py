"""Configure command for debug CLI."""

import json
from typing import Any, Optional

import click

from ..debug_config import DebugConfigManager
from ..k8s import K8sClient, RuntimeDetector
from ..k8s.client import K8sClientError
from ..k8s.detection import AppEndpointDetector


def register_configure_command(debug_group: click.Group) -> None:
    """Register the configure command with the debug group."""

    @debug_group.command()
    @click.option("--add", "add_name", help="Add a new environment with this name")
    @click.option(
        "--list", "list_envs", is_flag=True, help="List configured environments"
    )
    @click.option("--show", "show_env", is_flag=True, help="Show current configuration")
    @click.option("--default", "set_default", help="Set default environment")
    @click.option("--remove", "remove_name", help="Remove an environment")
    @click.option("--test", "test_conn", is_flag=True, help="Test cluster connectivity")
    @click.option(
        "--refresh",
        "refresh_env",
        help="Re-run detection and refresh config for an environment",
    )
    @click.pass_context
    def configure(
        ctx: click.Context,
        add_name: Optional[str],
        list_envs: bool,
        show_env: bool,
        set_default: Optional[str],
        remove_name: Optional[str],
        test_conn: bool,
        refresh_env: Optional[str],
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

        if refresh_env:
            _refresh_environment(config_manager, refresh_env)
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
        routing = env.get_routing_config()
        if routing:
            click.echo("  Runtime routing:")
            if routing.routing_mode:
                click.echo(f"    Mode:      {routing.routing_mode}")
            if routing.url_pattern:
                click.echo(f"    Pattern:   {routing.url_pattern}")
            elif routing.base_url:
                click.echo(f"    Base URL:  {routing.base_url}")
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


def _detect_runtime_config(
    env: Any, app_client: K8sClient
) -> tuple[Any, RuntimeDetector]:
    """Detect runtime configuration from clusters.

    Returns:
        Tuple of (detected config or None, detector used for app cluster)
    """
    from ..debug_config import EnvironmentConfig

    env_config: EnvironmentConfig = env
    runtime_config = env_config.get_runtime_config()
    is_two_cluster = runtime_config.kube_context != env_config.app.kube_context

    detector = RuntimeDetector(app_client)
    detected = detector.detect(env_config.app.namespace)

    if detected is None and is_two_cluster:
        try:
            runtime_client = K8sClient(runtime_config.kube_context)
            runtime_detector = RuntimeDetector(runtime_client)
            detected = runtime_detector.detect(runtime_config.namespace)
        except K8sClientError as e:
            click.echo(f"⚠ Could not connect to runtime cluster: {e}")

    return detected, detector


def _update_routing_config(
    config_manager: DebugConfigManager,
    env_name: str,
    env: Any,
    detected: Any,
    detector: RuntimeDetector,
) -> list[str]:
    """Update routing config and return list of changes made."""
    from ..debug_config import EnvironmentConfig

    env_config: EnvironmentConfig = env
    changes: list[str] = []

    if detected:
        has_runtime_api = detector.find_runtime_api_deployment(env_config.app.namespace)
        if has_runtime_api:
            click.echo("✓ Found runtime-api deployment")
        else:
            click.echo("✓ Found runtime routing config (from app deployment)")

        old_routing = env_config.get_routing_config()
        new_url_pattern = detected.runtime_url_pattern
        new_routing_mode = detected.runtime_routing_mode
        new_base_url = detected.runtime_base_url

        if new_url_pattern or new_routing_mode or new_base_url:
            routing_desc = detected.get_routing_description()
            click.echo(f"✓ Runtime routing: {routing_desc}")

            if old_routing:
                if old_routing.url_pattern != new_url_pattern:
                    changes.append(
                        f"URL pattern: {old_routing.url_pattern or 'N/A'} → "
                        f"{new_url_pattern or 'N/A'}"
                    )
                if old_routing.routing_mode != new_routing_mode:
                    changes.append(
                        f"Routing mode: {old_routing.routing_mode or 'N/A'} → "
                        f"{new_routing_mode or 'N/A'}"
                    )
                if old_routing.base_url != new_base_url:
                    changes.append(
                        f"Base URL: {old_routing.base_url or 'N/A'} → "
                        f"{new_base_url or 'N/A'}"
                    )
            else:
                changes.append("Added routing configuration")

            config_manager.update_environment_routing(
                name=env_name,
                runtime_url_pattern=new_url_pattern,
                runtime_routing_mode=new_routing_mode,
                runtime_base_url=new_base_url,
            )
        elif old_routing:
            click.echo("⚠ No routing config detected (previously had routing)")
            changes.append("Removed routing configuration")
            config_manager.update_environment_routing(name=env_name)
        else:
            click.echo("  No routing config detected")
    else:
        click.echo("⚠ Could not detect runtime configuration")
        click.echo("  (runtime-api deployment not found)")

    return changes


def _detect_and_report_endpoint(app_client: K8sClient, namespace: str) -> None:
    """Detect and report application endpoint."""
    click.echo()
    click.echo("Detecting application endpoint...")

    try:
        endpoint_detector = AppEndpointDetector(app_client)
        endpoint = endpoint_detector.detect(namespace)
        if endpoint:
            click.echo(f"✓ Detected endpoint: {endpoint.url}")
            click.echo(f"  Source: {endpoint.source}")
        else:
            click.echo("⚠ Could not detect application endpoint")
    except K8sClientError as e:
        click.echo(f"⚠ Could not detect endpoint: {e}")


def _report_config_changes(changes: list[str]) -> None:
    """Report configuration changes to the user."""
    click.echo()
    if changes:
        click.echo("Changes applied:")
        for change in changes:
            click.echo(f"  • {change}")
        click.echo()
        click.echo("✓ Configuration updated")
    else:
        click.echo("✓ No changes needed - configuration is up to date")


def _refresh_environment(config_manager: DebugConfigManager, env_name: str) -> None:
    """Re-run detection and refresh config for an existing environment."""
    env = config_manager.get_environment(env_name)
    if not env:
        raise click.ClickException(f"Environment '{env_name}' not found")

    click.echo(f"Refreshing configuration for '{env_name}'...")
    click.echo()

    try:
        app_client = K8sClient(env.app.kube_context)
    except K8sClientError as e:
        raise click.ClickException(f"Could not connect to app cluster: {e}") from None

    click.echo("Detecting runtime configuration...")
    detected, detector = _detect_runtime_config(env, app_client)

    changes = _update_routing_config(config_manager, env_name, env, detected, detector)

    _detect_and_report_endpoint(app_client, env.app.namespace)
    _report_config_changes(changes)


def _select_runtime_context(contexts: list[dict[str, Any]], app_context: str) -> str:
    """Prompt user to select runtime cluster context.

    Args:
        contexts: List of available kubectl contexts
        app_context: The application cluster context name

    Returns:
        The selected runtime cluster context name
    """
    click.echo("Runtime Cluster (where runtime pods run)")
    click.echo("-" * 40)

    same_cluster = click.confirm(
        "Are runtime pods in the same cluster as the app?", default=True
    )

    if same_cluster:
        click.echo(f"  Context:   {app_context} (same as app)")
        return app_context

    click.echo("Available kubectl contexts:")
    for i, ctx in enumerate(contexts, 1):
        marker = " (app)" if ctx["name"] == app_context else ""
        click.echo(f"  {i}. {ctx['name']}{marker}")

    ctx_choice = click.prompt(
        f"Select runtime cluster context [1-{len(contexts)}]",
        type=click.IntRange(1, len(contexts)),
    )
    selected_name: str = contexts[ctx_choice - 1]["name"]
    return selected_name


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
        runtime_url_pattern: Optional[str] = None
        runtime_routing_mode: Optional[str] = None
        runtime_base_url: Optional[str] = None

        if detected:
            click.echo("✓ Found runtime-api deployment")
            click.echo(f"✓ Detected: {detected.get_description()}")

            # Show routing config if detected
            routing_desc = detected.get_routing_description()
            if routing_desc:
                click.echo(f"✓ Runtime routing: {routing_desc}")
                runtime_url_pattern = detected.runtime_url_pattern
                runtime_routing_mode = detected.runtime_routing_mode
                runtime_base_url = detected.runtime_base_url

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
            runtime_context = _select_runtime_context(contexts, app_context)
            runtime_namespace = click.prompt(
                "Runtime namespace", default="runtime-pods"
            )
    except K8sClientError as e:
        click.echo(f"⚠ Could not connect to cluster: {e}")
        click.echo()
        runtime_context = _select_runtime_context(contexts, app_context)
        runtime_namespace = click.prompt("Runtime namespace", default="runtime-pods")
        runtime_url_pattern = None
        runtime_routing_mode = None
        runtime_base_url = None

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
        runtime_url_pattern=runtime_url_pattern,
        runtime_routing_mode=runtime_routing_mode,
        runtime_base_url=runtime_base_url,
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
