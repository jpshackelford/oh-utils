"""Utility functions for debug commands."""

from typing import Optional

import click

from ..debug_config import DebugConfigManager, EnvironmentConfig
from ..k8s import K8sClient
from ..k8s.client import K8sClientError


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


def parse_duration(duration: str) -> int:
    """Parse duration string to seconds.

    Args:
        duration: Duration string like "1h", "30m", "300s", "2d",
            or plain number (treated as minutes)

    Returns:
        Duration in seconds
    """
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
