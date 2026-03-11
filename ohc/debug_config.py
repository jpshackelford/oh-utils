"""
Debug configuration management for OpenHands Enterprise troubleshooting.

Handles debug environment configuration storage and retrieval following
XDG Base Directory Specification, consistent with the main ohc config.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ClusterConfig:
    """Configuration for a Kubernetes cluster connection."""

    kube_context: str
    namespace: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClusterConfig":
        return cls(
            kube_context=data.get("kube_context", ""),
            namespace=data.get("namespace", ""),
        )


@dataclass
class RuntimeRoutingConfig:
    """Configuration for runtime URL routing."""

    url_pattern: Optional[str] = None  # e.g., "https://server/{runtime_id}"
    routing_mode: Optional[str] = None  # "path" or "subdomain"
    base_url: Optional[str] = None  # e.g., "runtime.example.com"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.url_pattern:
            result["url_pattern"] = self.url_pattern
        if self.routing_mode:
            result["routing_mode"] = self.routing_mode
        if self.base_url:
            result["base_url"] = self.base_url
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeRoutingConfig":
        return cls(
            url_pattern=data.get("url_pattern"),
            routing_mode=data.get("routing_mode"),
            base_url=data.get("base_url"),
        )

    def is_configured(self) -> bool:
        """Check if any routing config is set."""
        return bool(self.url_pattern or self.routing_mode or self.base_url)

    def get_description(self) -> Optional[str]:
        """Get human-readable description of routing config."""
        if not self.is_configured():
            return None

        parts = []
        if self.routing_mode:
            parts.append(f"Mode: {self.routing_mode}")
        if self.url_pattern:
            parts.append(f"Pattern: {self.url_pattern}")
        elif self.base_url:
            parts.append(f"Base URL: {self.base_url}")
        return ", ".join(parts) if parts else None


@dataclass
class EnvironmentConfig:
    """Configuration for a debug environment (app + runtime clusters)."""

    app: ClusterConfig
    runtime: Optional[ClusterConfig] = None
    routing: Optional[RuntimeRoutingConfig] = None

    def get_runtime_config(self) -> ClusterConfig:
        """Get runtime config, falling back to app config if not specified."""
        if self.runtime and self.runtime.kube_context:
            return self.runtime
        # Default: same cluster as app, namespace defaults to runtime-pods
        return ClusterConfig(
            kube_context=self.app.kube_context,
            namespace=self.runtime.namespace if self.runtime else "runtime-pods",
        )

    def get_routing_config(self) -> Optional[RuntimeRoutingConfig]:
        """Get routing config if configured."""
        if self.routing and self.routing.is_configured():
            return self.routing
        return None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"app": self.app.to_dict()}
        if self.runtime:
            result["runtime"] = self.runtime.to_dict()
        if self.routing and self.routing.is_configured():
            result["routing"] = self.routing.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentConfig":
        app = ClusterConfig.from_dict(data.get("app", {}))
        runtime = None
        if "runtime" in data:
            runtime = ClusterConfig.from_dict(data["runtime"])
        routing = None
        if "routing" in data:
            routing = RuntimeRoutingConfig.from_dict(data["routing"])
        return cls(app=app, runtime=runtime, routing=routing)


@dataclass
class DebugConfig:
    """Root configuration for debug environments."""

    environments: Dict[str, EnvironmentConfig] = field(default_factory=dict)
    default_environment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environments": {
                name: env.to_dict() for name, env in self.environments.items()
            },
            "default_environment": self.default_environment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugConfig":
        environments = {
            name: EnvironmentConfig.from_dict(env_data)
            for name, env_data in data.get("environments", {}).items()
        }
        return cls(
            environments=environments,
            default_environment=data.get("default_environment"),
        )


class DebugConfigManager:
    """
    Manages debug configuration for OpenHands Enterprise troubleshooting.

    Configuration is stored in JSON format at ~/.config/ohc/debug.json
    """

    def __init__(self) -> None:
        """Initialize configuration manager and ensure config directory exists."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "debug.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_dir(self) -> Path:
        """Get configuration directory following XDG Base Directory Specification."""
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "ohc"
        return Path.home() / ".config" / "ohc"

    def load_config(self) -> DebugConfig:
        """Load configuration from file."""
        if not self.config_file.exists():
            return DebugConfig()

        try:
            with open(self.config_file) as f:
                data = json.load(f)
                return DebugConfig.from_dict(data)
        except (OSError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to load debug configuration: {e}") from e

    def save_config(self, config: DebugConfig) -> None:
        """Save configuration to file with secure permissions."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            os.chmod(self.config_file, 0o600)
        except OSError as e:
            raise Exception(f"Failed to save debug configuration: {e}") from e

    def get_environment(
        self, name: Optional[str] = None
    ) -> Optional[EnvironmentConfig]:
        """Get configuration for a specific environment or the default."""
        config = self.load_config()

        if name:
            return config.environments.get(name)

        # Return default environment if no specific one requested
        if config.default_environment:
            return config.environments.get(config.default_environment)

        # If no default set, return the first environment if any exist
        if config.environments:
            return next(iter(config.environments.values()))

        return None

    def get_environment_name(self, name: Optional[str] = None) -> Optional[str]:
        """Get the name of the environment that would be used."""
        config = self.load_config()

        if name and name in config.environments:
            return name

        default_env = config.default_environment
        if default_env and default_env in config.environments:
            return default_env

        if config.environments:
            return next(iter(config.environments.keys()))

        return None

    def add_environment(
        self,
        name: str,
        app_context: str,
        app_namespace: str,
        runtime_context: Optional[str] = None,
        runtime_namespace: str = "runtime-pods",
        set_default: bool = False,
        runtime_url_pattern: Optional[str] = None,
        runtime_routing_mode: Optional[str] = None,
        runtime_base_url: Optional[str] = None,
    ) -> None:
        """Add a new environment configuration."""
        config = self.load_config()

        app_config = ClusterConfig(kube_context=app_context, namespace=app_namespace)
        runtime_config = ClusterConfig(
            kube_context=runtime_context or app_context,
            namespace=runtime_namespace,
        )

        # Create routing config if any routing info provided
        routing_config = None
        if runtime_url_pattern or runtime_routing_mode or runtime_base_url:
            routing_config = RuntimeRoutingConfig(
                url_pattern=runtime_url_pattern,
                routing_mode=runtime_routing_mode,
                base_url=runtime_base_url,
            )

        env_config = EnvironmentConfig(
            app=app_config, runtime=runtime_config, routing=routing_config
        )

        config.environments[name] = env_config

        if set_default or not config.default_environment:
            config.default_environment = name

        self.save_config(config)

    def update_environment_routing(
        self,
        name: str,
        runtime_url_pattern: Optional[str] = None,
        runtime_routing_mode: Optional[str] = None,
        runtime_base_url: Optional[str] = None,
    ) -> bool:
        """Update routing configuration for an existing environment.

        Returns True if environment exists and was updated.
        """
        config = self.load_config()

        if name not in config.environments:
            return False

        env = config.environments[name]

        # Create or update routing config
        if runtime_url_pattern or runtime_routing_mode or runtime_base_url:
            env.routing = RuntimeRoutingConfig(
                url_pattern=runtime_url_pattern,
                routing_mode=runtime_routing_mode,
                base_url=runtime_base_url,
            )
        else:
            env.routing = None

        self.save_config(config)
        return True

    def remove_environment(self, name: str) -> bool:
        """Remove an environment configuration. Returns True if found and removed."""
        config = self.load_config()

        if name not in config.environments:
            return False

        del config.environments[name]

        if config.default_environment == name:
            config.default_environment = (
                next(iter(config.environments.keys())) if config.environments else None
            )

        self.save_config(config)
        return True

    def set_default_environment(self, name: str) -> bool:
        """Set an environment as the default. Returns True if successful."""
        config = self.load_config()

        if name not in config.environments:
            return False

        config.default_environment = name
        self.save_config(config)
        return True

    def list_environments(self) -> List[str]:
        """Get list of all configured environment names."""
        config = self.load_config()
        return list(config.environments.keys())

    def get_default_environment_name(self) -> Optional[str]:
        """Get the name of the default environment."""
        config = self.load_config()
        return config.default_environment
