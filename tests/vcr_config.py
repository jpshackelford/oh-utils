"""
VCR.py configuration for recording HTTP interactions.

This module provides configuration for VCR.py to record and replay
HTTP interactions for integration testing.
"""

from pathlib import Path

import vcr  # type: ignore[import-untyped]


def create_vcr() -> vcr.VCR:
    """Create a configured VCR instance for API testing."""
    cassettes_dir = Path(__file__).parent / "cassettes"
    cassettes_dir.mkdir(exist_ok=True)

    return vcr.VCR(
        # Where to store cassettes
        cassette_library_dir=str(cassettes_dir),
        # Record mode: 'once' records new interactions, 'none' only replays
        record_mode="once",
        # Match requests by method, URI, and body
        match_on=["method", "uri", "body"],
        # Filter out sensitive headers
        filter_headers=["X-Session-API-Key", "Authorization"],
        # Filter sensitive data from request/response bodies
        filter_post_data_parameters=["api_key", "session_api_key"],
        # Decode compressed responses for easier inspection
        decode_compressed_response=True,
        # Custom serializer for better readability
        serializer="yaml",
        # Custom request matching for better control
        before_record_request=sanitize_request,
        before_record_response=sanitize_response,
    )


def sanitize_request(request):
    """Sanitize sensitive data from requests before recording."""
    # Replace API keys in headers
    if "X-Session-API-Key" in request.headers:
        request.headers["X-Session-API-Key"] = "fake-session-api-key"

    if "Authorization" in request.headers:
        request.headers["Authorization"] = "Bearer fake-api-key"

    # Replace sensitive data in URLs
    if "work-" in request.uri:
        # Replace runtime IDs with fake ones
        import re

        request.uri = re.sub(
            r"work-\d+-[a-z0-9]+", "work-1-fakeworkspace001", request.uri
        )

    return request


def sanitize_response(response):
    """Sanitize sensitive data from responses before recording."""
    # Only process JSON responses
    if response["headers"].get("content-type", [""])[0].startswith("application/json"):
        import json

        try:
            data = json.loads(response["body"]["string"])

            # Sanitize common sensitive fields
            data = _sanitize_json_data(data)

            response["body"]["string"] = json.dumps(data, separators=(",", ":"))
        except (json.JSONDecodeError, KeyError):
            # Skip sanitization if we can't parse the JSON
            pass

    return response


def _sanitize_json_data(data):
    """Recursively sanitize JSON data."""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key in ["id", "conversation_id"] and isinstance(value, str):
                # Replace UUIDs with fake ones
                sanitized[key] = "fake-uuid-" + str(hash(value))[:8]
            elif key == "title" and isinstance(value, str):
                sanitized[key] = "Example Conversation"
            elif key in ["runtime_id"] and isinstance(value, str):
                sanitized[key] = "work-1-fakeworkspace001"
            elif key in ["session_api_key"] and isinstance(value, str):
                sanitized[key] = "sess_fakexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            elif key in ["email"] and isinstance(value, str):
                sanitized[key] = "user@example.com"
            else:
                sanitized[key] = _sanitize_json_data(value)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_json_data(item) for item in data]
    else:
        return data


# Create a default VCR instance
default_vcr = create_vcr()
