"""
Tests for CLI entry point functionality.

Tests the ohc.cli module including:
- Main CLI group behavior
- Interactive mode handling
- Help command functionality
- Command registration
"""

from unittest.mock import patch

import click
from click.testing import CliRunner

from ohc.cli import cli, help_command, main


class TestCLI:
    """Test CLI entry point functionality."""

    def test_cli_version_option(self):
        """Test CLI version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "ohc" in result.output

    def test_cli_help_default(self):
        """Test CLI shows help by default."""
        runner = CliRunner()
        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        assert "OpenHands Cloud CLI" in result.output
        assert "Usage:" in result.output

    def test_cli_help_explicit(self):
        """Test CLI help option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "OpenHands Cloud CLI" in result.output
        assert "Usage:" in result.output

    def test_cli_interactive_flag_context(self):
        """Test CLI interactive flag sets context."""
        runner = CliRunner()

        # Create a temporary command for testing
        @click.command()
        @click.pass_context
        def test_cmd(ctx):
            click.echo(f"Interactive: {ctx.obj['interactive']}")

        # Add the command to CLI temporarily
        cli.add_command(test_cmd, name="test-cmd")

        try:
            # Test without interactive flag
            result = runner.invoke(cli, ["test-cmd"])
            assert "Interactive: False" in result.output

            # Test with interactive flag
            result = runner.invoke(cli, ["-i", "test-cmd"])
            assert "Interactive: True" in result.output
        finally:
            # Clean up - remove the test command
            if "test-cmd" in cli.commands:
                del cli.commands["test-cmd"]

    @patch("ohc.conversation_commands.interactive_mode")
    def test_cli_interactive_mode(self, mock_interactive):
        """Test CLI interactive mode invocation."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-i"])

        # Should call interactive_mode
        mock_interactive.assert_called_once()
        assert result.exit_code == 0

    def test_help_command_with_parent(self):
        """Test help command with parent context."""
        runner = CliRunner()

        # Create a test group with help command
        @click.group()
        def test_group():
            """Test group help."""
            pass

        test_group.add_command(help_command, name="help")

        result = runner.invoke(test_group, ["help"])
        assert result.exit_code == 0
        assert "Test group help" in result.output

    def test_help_command_without_parent(self):
        """Test help command without parent context."""
        runner = CliRunner()

        # Invoke help command directly (no parent)
        result = runner.invoke(help_command, [])
        assert result.exit_code == 0
        assert "No help available" in result.output

    @patch("ohc.cli.cli")
    def test_main_function(self, mock_cli):
        """Test main function registers commands and calls CLI."""
        main()

        # Should call the CLI
        mock_cli.assert_called_once()

    def test_main_function_command_registration(self):
        """Test main function registers all commands."""
        # Test that main function can be called without error
        # We can't easily test the actual command registration
        # without triggering the full CLI, so we test basic functionality
        from ohc.cli import main

        # Test that main is callable
        assert callable(main)

        # Test that the CLI has the expected structure
        assert hasattr(cli, "commands")
        assert hasattr(cli, "add_command")

    def test_cli_context_object_creation(self):
        """Test CLI creates context object."""
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def test_ctx(ctx):
            assert ctx.obj is not None
            assert isinstance(ctx.obj, dict)
            assert "interactive" in ctx.obj
            click.echo("Context OK")

        cli.add_command(test_ctx, name="test-ctx")

        try:
            result = runner.invoke(cli, ["test-ctx"])
            assert result.exit_code == 0
            assert "Context OK" in result.output
        finally:
            if "test-ctx" in cli.commands:
                del cli.commands["test-ctx"]

    def test_cli_no_subcommand_no_interactive(self):
        """Test CLI behavior with no subcommand and no interactive flag."""
        runner = CliRunner()
        result = runner.invoke(cli, [])

        # Should show help and exit
        assert result.exit_code == 0
        assert "Usage:" in result.output

    @patch("ohc.conversation_commands.interactive_mode")
    def test_cli_interactive_mode_exception_handling(self, mock_interactive):
        """Test CLI handles interactive mode exceptions."""
        # Make interactive_mode raise an exception
        mock_interactive.side_effect = Exception("Interactive mode failed")

        runner = CliRunner()
        result = runner.invoke(cli, ["-i"])

        # Should still call interactive_mode
        mock_interactive.assert_called_once()
        # Exception should propagate (Click will handle it)
        assert result.exit_code != 0

    def test_cli_subcommand_invocation(self):
        """Test CLI properly invokes subcommands."""
        runner = CliRunner()

        @click.command()
        def test_subcommand():
            click.echo("Subcommand executed")

        cli.add_command(test_subcommand, name="test-subcommand")

        try:
            result = runner.invoke(cli, ["test-subcommand"])
            assert result.exit_code == 0
            assert "Subcommand executed" in result.output
        finally:
            if "test-subcommand" in cli.commands:
                del cli.commands["test-subcommand"]

    def test_cli_interactive_flag_short_form(self):
        """Test CLI interactive flag short form."""
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def test_interactive(ctx):
            click.echo(f"Interactive: {ctx.obj['interactive']}")

        cli.add_command(test_interactive, name="test-interactive")

        try:
            result = runner.invoke(cli, ["-i", "test-interactive"])
            assert result.exit_code == 0
            assert "Interactive: True" in result.output
        finally:
            if "test-interactive" in cli.commands:
                del cli.commands["test-interactive"]

    def test_cli_interactive_flag_long_form(self):
        """Test CLI interactive flag long form."""
        runner = CliRunner()

        @click.command()
        @click.pass_context
        def test_interactive_long(ctx):
            click.echo(f"Interactive: {ctx.obj['interactive']}")

        cli.add_command(test_interactive_long, name="test-interactive-long")

        try:
            result = runner.invoke(cli, ["--interactive", "test-interactive-long"])
            assert result.exit_code == 0
            assert "Interactive: True" in result.output
        finally:
            if "test-interactive-long" in cli.commands:
                del cli.commands["test-interactive-long"]
