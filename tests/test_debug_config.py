"""Tests for debug configuration management."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ohc.debug_config import (
    ClusterConfig,
    DebugConfig,
    DebugConfigManager,
    EnvironmentConfig,
    RuntimeRoutingConfig,
)


class TestClusterConfig:
    """Tests for ClusterConfig dataclass."""

    def test_to_dict(self) -> None:
        config = ClusterConfig(kube_context="my-context", namespace="my-namespace")
        assert config.to_dict() == {
            "kube_context": "my-context",
            "namespace": "my-namespace",
        }

    def test_from_dict(self) -> None:
        data = {"kube_context": "ctx", "namespace": "ns"}
        config = ClusterConfig.from_dict(data)
        assert config.kube_context == "ctx"
        assert config.namespace == "ns"

    def test_from_dict_missing_keys(self) -> None:
        config = ClusterConfig.from_dict({})
        assert config.kube_context == ""
        assert config.namespace == ""


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig dataclass."""

    def test_get_runtime_config_explicit(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        runtime = ClusterConfig("runtime-ctx", "runtime-ns")
        env = EnvironmentConfig(app=app, runtime=runtime)

        result = env.get_runtime_config()
        assert result.kube_context == "runtime-ctx"
        assert result.namespace == "runtime-ns"

    def test_get_runtime_config_defaults_to_app_context(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        env = EnvironmentConfig(app=app, runtime=None)

        result = env.get_runtime_config()
        assert result.kube_context == "app-ctx"
        assert result.namespace == "runtime-pods"

    def test_get_runtime_config_uses_runtime_namespace(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        runtime = ClusterConfig("", "custom-runtime-ns")
        env = EnvironmentConfig(app=app, runtime=runtime)

        result = env.get_runtime_config()
        assert result.kube_context == "app-ctx"
        assert result.namespace == "custom-runtime-ns"

    def test_to_dict_with_runtime(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        runtime = ClusterConfig("runtime-ctx", "runtime-ns")
        env = EnvironmentConfig(app=app, runtime=runtime)

        result = env.to_dict()
        assert result == {
            "app": {"kube_context": "app-ctx", "namespace": "app-ns"},
            "runtime": {"kube_context": "runtime-ctx", "namespace": "runtime-ns"},
        }

    def test_to_dict_without_runtime(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        env = EnvironmentConfig(app=app, runtime=None)

        result = env.to_dict()
        assert result == {
            "app": {"kube_context": "app-ctx", "namespace": "app-ns"},
        }

    def test_to_dict_with_routing(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        routing = RuntimeRoutingConfig(
            url_pattern="https://runtime.example.com/{runtime_id}",
            routing_mode="path",
        )
        env = EnvironmentConfig(app=app, routing=routing)

        result = env.to_dict()
        assert "routing" in result
        assert (
            result["routing"]["url_pattern"]
            == "https://runtime.example.com/{runtime_id}"
        )
        assert result["routing"]["routing_mode"] == "path"

    def test_get_routing_config(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        routing = RuntimeRoutingConfig(
            url_pattern="https://runtime.example.com/{runtime_id}",
            routing_mode="path",
        )
        env = EnvironmentConfig(app=app, routing=routing)

        result = env.get_routing_config()
        assert result is not None
        assert result.url_pattern == "https://runtime.example.com/{runtime_id}"

    def test_get_routing_config_none(self) -> None:
        app = ClusterConfig("app-ctx", "app-ns")
        env = EnvironmentConfig(app=app)

        result = env.get_routing_config()
        assert result is None

    def test_from_dict_with_routing(self) -> None:
        data = {
            "app": {"kube_context": "ctx", "namespace": "ns"},
            "routing": {
                "url_pattern": "https://runtime.example.com/{runtime_id}",
                "routing_mode": "path",
                "base_url": "runtime.example.com",
            },
        }
        env = EnvironmentConfig.from_dict(data)
        assert env.routing is not None
        assert env.routing.url_pattern == "https://runtime.example.com/{runtime_id}"
        assert env.routing.routing_mode == "path"
        assert env.routing.base_url == "runtime.example.com"


class TestRuntimeRoutingConfig:
    """Tests for RuntimeRoutingConfig dataclass."""

    def test_to_dict_full(self) -> None:
        config = RuntimeRoutingConfig(
            url_pattern="https://runtime.example.com/{runtime_id}",
            routing_mode="path",
            base_url="runtime.example.com",
        )
        result = config.to_dict()
        assert result == {
            "url_pattern": "https://runtime.example.com/{runtime_id}",
            "routing_mode": "path",
            "base_url": "runtime.example.com",
        }

    def test_to_dict_partial(self) -> None:
        config = RuntimeRoutingConfig(routing_mode="subdomain")
        result = config.to_dict()
        assert result == {"routing_mode": "subdomain"}

    def test_to_dict_empty(self) -> None:
        config = RuntimeRoutingConfig()
        result = config.to_dict()
        assert result == {}

    def test_from_dict(self) -> None:
        data = {
            "url_pattern": "https://runtime.example.com/{runtime_id}",
            "routing_mode": "path",
        }
        config = RuntimeRoutingConfig.from_dict(data)
        assert config.url_pattern == "https://runtime.example.com/{runtime_id}"
        assert config.routing_mode == "path"
        assert config.base_url is None

    def test_is_configured_true(self) -> None:
        config = RuntimeRoutingConfig(routing_mode="path")
        assert config.is_configured() is True

    def test_is_configured_false(self) -> None:
        config = RuntimeRoutingConfig()
        assert config.is_configured() is False

    def test_get_description_with_pattern(self) -> None:
        config = RuntimeRoutingConfig(
            url_pattern="https://runtime.example.com/{runtime_id}",
            routing_mode="path",
        )
        desc = config.get_description()
        assert desc is not None
        assert "path" in desc
        assert "https://runtime.example.com/{runtime_id}" in desc

    def test_get_description_with_base_url(self) -> None:
        config = RuntimeRoutingConfig(
            routing_mode="subdomain",
            base_url="runtime.example.com",
        )
        desc = config.get_description()
        assert desc is not None
        assert "subdomain" in desc
        assert "runtime.example.com" in desc

    def test_get_description_none(self) -> None:
        config = RuntimeRoutingConfig()
        assert config.get_description() is None


class TestDebugConfig:
    """Tests for DebugConfig dataclass."""

    def test_empty_config(self) -> None:
        config = DebugConfig()
        assert config.environments == {}
        assert config.default_environment is None

    def test_to_dict(self) -> None:
        app = ClusterConfig("ctx", "ns")
        env = EnvironmentConfig(app=app)
        config = DebugConfig(
            environments={"prod": env},
            default_environment="prod",
        )

        result = config.to_dict()
        assert result["default_environment"] == "prod"
        assert "prod" in result["environments"]

    def test_from_dict(self) -> None:
        data = {
            "environments": {
                "production": {
                    "app": {"kube_context": "prod-ctx", "namespace": "openhands"},
                    "runtime": {
                        "kube_context": "prod-ctx",
                        "namespace": "runtime-pods",
                    },
                }
            },
            "default_environment": "production",
        }
        config = DebugConfig.from_dict(data)
        assert config.default_environment == "production"
        assert "production" in config.environments
        assert config.environments["production"].app.kube_context == "prod-ctx"


class TestDebugConfigManager:
    """Tests for DebugConfigManager."""

    @pytest.fixture
    def temp_config_dir(self) -> Path:
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> DebugConfigManager:
        """Create a config manager with temp directory."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = DebugConfigManager()
            yield manager

    def test_load_empty_config(self, manager: DebugConfigManager) -> None:
        config = manager.load_config()
        assert config.environments == {}
        assert config.default_environment is None

    def test_save_and_load_config(self, manager: DebugConfigManager) -> None:
        app = ClusterConfig("ctx", "ns")
        env = EnvironmentConfig(app=app)
        config = DebugConfig(environments={"test": env}, default_environment="test")

        manager.save_config(config)
        loaded = manager.load_config()

        assert loaded.default_environment == "test"
        assert "test" in loaded.environments

    def test_add_environment(self, manager: DebugConfigManager) -> None:
        manager.add_environment(
            name="production",
            app_context="gke_project_region_cluster",
            app_namespace="openhands",
            runtime_context="gke_project_region_cluster",
            runtime_namespace="runtime-pods",
            set_default=True,
        )

        config = manager.load_config()
        assert "production" in config.environments
        assert config.default_environment == "production"

    def test_add_environment_sets_first_as_default(
        self, manager: DebugConfigManager
    ) -> None:
        manager.add_environment(
            name="staging",
            app_context="ctx",
            app_namespace="ns",
        )

        config = manager.load_config()
        assert config.default_environment == "staging"

    def test_remove_environment(self, manager: DebugConfigManager) -> None:
        manager.add_environment(name="test", app_context="ctx", app_namespace="ns")
        assert manager.remove_environment("test") is True
        assert manager.list_environments() == []

    def test_remove_nonexistent_environment(self, manager: DebugConfigManager) -> None:
        assert manager.remove_environment("nonexistent") is False

    def test_set_default_environment(self, manager: DebugConfigManager) -> None:
        manager.add_environment(name="env1", app_context="ctx1", app_namespace="ns1")
        manager.add_environment(name="env2", app_context="ctx2", app_namespace="ns2")

        assert manager.set_default_environment("env2") is True
        assert manager.get_default_environment_name() == "env2"

    def test_set_default_nonexistent(self, manager: DebugConfigManager) -> None:
        assert manager.set_default_environment("nonexistent") is False

    def test_get_environment(self, manager: DebugConfigManager) -> None:
        manager.add_environment(
            name="test",
            app_context="my-ctx",
            app_namespace="my-ns",
        )

        env = manager.get_environment("test")
        assert env is not None
        assert env.app.kube_context == "my-ctx"
        assert env.app.namespace == "my-ns"

    def test_get_environment_default(self, manager: DebugConfigManager) -> None:
        manager.add_environment(
            name="default-env", app_context="ctx", app_namespace="ns"
        )

        env = manager.get_environment()
        assert env is not None

    def test_get_environment_nonexistent(self, manager: DebugConfigManager) -> None:
        assert manager.get_environment("nonexistent") is None

    def test_list_environments(self, manager: DebugConfigManager) -> None:
        manager.add_environment(name="env1", app_context="ctx1", app_namespace="ns1")
        manager.add_environment(name="env2", app_context="ctx2", app_namespace="ns2")

        envs = manager.list_environments()
        assert "env1" in envs
        assert "env2" in envs

    @pytest.mark.skipif(
        sys.platform == "win32", reason="File permissions work differently on Windows"
    )
    def test_config_file_permissions(self, manager: DebugConfigManager) -> None:
        manager.add_environment(name="test", app_context="ctx", app_namespace="ns")

        # Check file permissions are restrictive
        stat_result = os.stat(manager.config_file)
        permissions = stat_result.st_mode & 0o777
        assert permissions == 0o600

    def test_add_environment_with_routing(self, manager: DebugConfigManager) -> None:
        manager.add_environment(
            name="production",
            app_context="gke_project_region_cluster",
            app_namespace="openhands",
            runtime_url_pattern="https://runtime.example.com/{runtime_id}",
            runtime_routing_mode="path",
            runtime_base_url="runtime.example.com",
        )

        config = manager.load_config()
        env = config.environments["production"]
        assert env.routing is not None
        assert env.routing.url_pattern == "https://runtime.example.com/{runtime_id}"
        assert env.routing.routing_mode == "path"
        assert env.routing.base_url == "runtime.example.com"

    def test_update_environment_routing(self, manager: DebugConfigManager) -> None:
        manager.add_environment(
            name="test",
            app_context="ctx",
            app_namespace="ns",
        )

        # Update routing
        result = manager.update_environment_routing(
            name="test",
            runtime_url_pattern="https://runtime.example.com/{runtime_id}",
            runtime_routing_mode="path",
        )
        assert result is True

        config = manager.load_config()
        env = config.environments["test"]
        assert env.routing is not None
        assert env.routing.url_pattern == "https://runtime.example.com/{runtime_id}"

    def test_update_environment_routing_nonexistent(
        self, manager: DebugConfigManager
    ) -> None:
        result = manager.update_environment_routing(
            name="nonexistent",
            runtime_url_pattern="https://example.com/{runtime_id}",
        )
        assert result is False

    def test_update_environment_routing_clear(
        self, manager: DebugConfigManager
    ) -> None:
        # Add env with routing
        manager.add_environment(
            name="test",
            app_context="ctx",
            app_namespace="ns",
            runtime_url_pattern="https://runtime.example.com/{runtime_id}",
        )

        # Clear routing by not passing any routing params
        manager.update_environment_routing(name="test")

        config = manager.load_config()
        env = config.environments["test"]
        assert env.routing is None
