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
