"""Tests for debug CLI commands."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from ohc.cli import cli
from ohc.conversation_commands import conv
from ohc.debug import debug
from ohc.debug_config import DebugConfigManager
from ohc.server_commands import server


@pytest.fixture
def cli_with_commands() -> click.Group:
    """Create CLI with all commands registered."""
    # Register commands like main() does
    cli.add_command(server)
    cli.add_command(conv)
    cli.add_command(debug)
    return cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir() -> Path:
    """Create a temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_manager(temp_config_dir: Path) -> DebugConfigManager:
    """Create a config manager with temp directory."""
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
        manager = DebugConfigManager()
        yield manager


class TestDebugGroup:
    """Tests for the main debug command group."""

    def test_debug_help(
        self, runner: CliRunner, cli_with_commands: click.Group
    ) -> None:
        result = runner.invoke(cli_with_commands, ["debug", "--help"])
        assert result.exit_code == 0
        assert "Debug OpenHands Enterprise deployments" in result.output

    def test_debug_shows_commands(
        self, runner: CliRunner, cli_with_commands: click.Group
    ) -> None:
        result = runner.invoke(cli_with_commands, ["debug", "--help"])
        assert "configure" in result.output
        assert "health" in result.output
        assert "runtime" in result.output
        assert "list" in result.output
        assert "app" in result.output


class TestConfigureCommand:
    """Tests for the configure command."""

    def test_configure_list_empty(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_with_commands, ["debug", "configure", "--list"])
            assert result.exit_code == 0
            assert "No environments configured" in result.output

    def test_configure_list_with_environments(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            # First add an environment
            manager = DebugConfigManager()
            manager.add_environment(
                name="production",
                app_context="test-ctx",
                app_namespace="openhands",
            )

            result = runner.invoke(cli_with_commands, ["debug", "configure", "--list"])
            assert result.exit_code == 0
            assert "production" in result.output

    def test_configure_show_empty(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_with_commands, ["debug", "configure", "--show"])
            assert result.exit_code == 0
            assert "No environments configured" in result.output

    def test_configure_show_with_environment(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = DebugConfigManager()
            manager.add_environment(
                name="production",
                app_context="gke_project_region_cluster",
                app_namespace="openhands",
                runtime_namespace="runtime-pods",
            )

            result = runner.invoke(cli_with_commands, ["debug", "configure", "--show"])
            assert result.exit_code == 0
            assert "production" in result.output
            assert "openhands" in result.output

    def test_configure_show_json(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = DebugConfigManager()
            manager.add_environment(
                name="production",
                app_context="test-ctx",
                app_namespace="openhands",
            )

            result = runner.invoke(
                cli_with_commands, ["debug", "--output", "json", "configure", "--show"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "environments" in data
            assert "production" in data["environments"]

    def test_configure_set_default(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = DebugConfigManager()
            manager.add_environment(
                name="env1", app_context="ctx1", app_namespace="ns1"
            )
            manager.add_environment(
                name="env2", app_context="ctx2", app_namespace="ns2"
            )

            result = runner.invoke(
                cli_with_commands, ["debug", "configure", "--default", "env2"]
            )
            assert result.exit_code == 0
            assert "env2" in result.output
            assert "set as default" in result.output

    def test_configure_set_default_nonexistent(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(
                cli_with_commands, ["debug", "configure", "--default", "nonexistent"]
            )
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_configure_remove(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            manager = DebugConfigManager()
            manager.add_environment(name="test", app_context="ctx", app_namespace="ns")

            result = runner.invoke(
                cli_with_commands, ["debug", "configure", "--remove", "test"]
            )
            assert result.exit_code == 0
            assert "removed" in result.output

    def test_configure_remove_nonexistent(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(
                cli_with_commands, ["debug", "configure", "--remove", "nonexistent"]
            )
            assert result.exit_code != 0
            assert "not found" in result.output


class TestHealthCommand:
    """Tests for the health command."""

    def test_health_not_configured(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_with_commands, ["debug", "health"])
            assert result.exit_code != 0
            assert "No debug environment configured" in result.output


class TestRuntimeCommand:
    """Tests for the runtime command."""

    def test_runtime_help(
        self, runner: CliRunner, cli_with_commands: click.Group
    ) -> None:
        result = runner.invoke(cli_with_commands, ["debug", "runtime", "--help"])
        assert result.exit_code == 0
        assert "Investigate a specific runtime" in result.output

    def test_runtime_not_configured(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(
                cli_with_commands, ["debug", "runtime", "test-runtime-id"]
            )
            assert result.exit_code != 0
            assert "No debug environment configured" in result.output


class TestListCommand:
    """Tests for the list command."""

    def test_list_help(self, runner: CliRunner, cli_with_commands: click.Group) -> None:
        result = runner.invoke(cli_with_commands, ["debug", "list", "--help"])
        assert result.exit_code == 0
        assert "List runtime pods" in result.output
        assert "--errors" in result.output
        assert "--restarts" in result.output
        assert "--oom" in result.output

    def test_list_not_configured(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_with_commands, ["debug", "list"])
            assert result.exit_code != 0
            assert "No debug environment configured" in result.output


class TestAppCommands:
    """Tests for the app subcommands."""

    def test_app_help(self, runner: CliRunner, cli_with_commands: click.Group) -> None:
        result = runner.invoke(cli_with_commands, ["debug", "app", "--help"])
        assert result.exit_code == 0
        assert "logs" in result.output
        assert "status" in result.output
        assert "pods" in result.output

    def test_app_logs_help(
        self, runner: CliRunner, cli_with_commands: click.Group
    ) -> None:
        result = runner.invoke(cli_with_commands, ["debug", "app", "logs", "--help"])
        assert result.exit_code == 0
        assert "--follow" in result.output
        assert "--since" in result.output
        assert "--component" in result.output

    def test_app_status_not_configured(
        self, runner: CliRunner, cli_with_commands: click.Group, temp_config_dir: Path
    ) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_with_commands, ["debug", "app", "status"])
            assert result.exit_code != 0
            assert "No debug environment configured" in result.output
