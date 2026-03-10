"""Configure command for debug CLI."""

import json
from typing import Optional

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
