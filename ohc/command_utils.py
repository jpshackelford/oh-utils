"""
Shared utilities and decorators for OpenHands CLI commands.

This module provides common functionality to eliminate code duplication across
CLI commands, including server configuration handling and conversation ID resolution.
"""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import click

from .api import OpenHandsAPI
from .config import ConfigManager

F = TypeVar("F", bound=Callable[..., Any])


def with_server_config(func: F) -> F:
    """
    Decorator to handle server configuration boilerplate for CLI commands.

    This decorator:
    1. Gets the server configuration from ConfigManager
    2. Handles missing server configuration with appropriate error messages
    3. Creates an OpenHandsAPI instance
    4. Passes the API instance to the decorated function as 'api' parameter

    The decorated function should accept an 'api' parameter of type OpenHandsAPI.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        server = kwargs.get("server")
        config_manager = ConfigManager()
        server_config = config_manager.get_server_config(server)

        if not server_config:
            if server:
                click.echo(f"✗ Server '{server}' not found.", err=True)
            else:
                click.echo(
                    "✗ No servers configured. Use 'ohc server add' to add a server.",
                    err=True,
                )
            return None

        api = OpenHandsAPI(server_config["api_key"], server_config["url"])
        kwargs["api"] = api
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def resolve_conversation_id(
    api: OpenHandsAPI, conversation_id_or_number: str
) -> Optional[str]:
    """
    Resolve conversation ID from number or partial ID.

    This function handles three cases:
    1. Numeric input (1, 2, 3...) - resolves to conversation by list position
    2. Partial ID (8 chars or less) - finds matching conversation by ID prefix
    3. Full ID - returns as-is

    Args:
        api: OpenHandsAPI instance for making API calls
        conversation_id_or_number: Either a number, partial ID, or full ID

    Returns:
        Full conversation ID if found, None if not found or ambiguous
    """
    try:
        # Try to parse as a number first
        conv_number = int(conversation_id_or_number)

        # Get the conversation list to find the conversation by number
        result = api.search_conversations(limit=100)
        conversations = result.get("results", [])

        if conv_number < 1 or conv_number > len(conversations):
            click.echo(
                f"✗ Conversation number {conv_number} is out of range "
                f"(1-{len(conversations)})",
                err=True,
            )
            return None

        conv_data = conversations[conv_number - 1]
        conversation_id = conv_data.get("conversation_id")
        return conversation_id if conversation_id else None

    except ValueError:
        # It's a conversation ID string - could be full or partial
        conv_id = conversation_id_or_number

        # If it's not a full UUID (36 chars), try to find a matching conversation
        if len(conv_id) < 36:
            result = api.search_conversations(limit=100)
            conversations = result.get("results", [])

            matches = [
                c
                for c in conversations
                if c.get("conversation_id", "").startswith(conv_id)
            ]

            if not matches:
                click.echo(
                    f"✗ No conversation found with ID starting with '{conv_id}'",
                    err=True,
                )
                return None
            elif len(matches) > 1:
                click.echo(
                    f"✗ Multiple conversations match '{conv_id}'. "
                    f"Please use a longer ID:",
                    err=True,
                )
                for match in matches[:5]:  # Show first 5 matches
                    match_id = match.get("conversation_id", "")
                    match_title = match.get("title", "Untitled")[:40]
                    click.echo(f"  {match_id} - {match_title}")
                return None
            else:
                # Single match found
                conversation_id = matches[0].get("conversation_id")
                return conversation_id if conversation_id else None
        else:
            # Assume it's a full conversation ID
            return conv_id


def handle_missing_server_config(server: Optional[str]) -> None:
    """
    Handle missing server configuration with appropriate error messages.

    Args:
        server: Server name that was requested (None for default)
    """
    if server:
        click.echo(f"✗ Server '{server}' not found.", err=True)
    else:
        click.echo(
            "✗ No servers configured. Use 'ohc server add' to add a server.",
            err=True,
        )
