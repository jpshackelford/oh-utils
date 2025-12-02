#!/usr/bin/env python3
"""
Sanitize OpenHands v1 API fixtures for safe sharing.

This script processes recorded API responses to remove sensitive information
like API keys, user IDs, and other personally identifiable information,
making the fixtures safe for version control and sharing.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict


class V1FixtureSanitizer:
    """Sanitizes OpenHands v1 API fixtures by removing sensitive data."""

    def __init__(self, fixtures_dir: Path):
        """Initialize the sanitizer with the fixtures directory."""
        self.fixtures_dir = fixtures_dir
        self.sanitized_dir = fixtures_dir / "sanitized"
        self.sanitized_dir.mkdir(exist_ok=True)

        # Track replacements for consistency
        self.replacements: Dict[str, str] = {}
        self.replacement_counter = 1

    def get_replacement(self, original: str, prefix: str = "SANITIZED") -> str:
        """Get a consistent replacement for a sensitive value."""
        if original in self.replacements:
            return self.replacements[original]

        replacement = f"{prefix}_{self.replacement_counter:03d}"
        self.replacements[original] = replacement
        self.replacement_counter += 1
        return replacement

    def sanitize_api_key(self, text: str) -> str:
        """Replace API keys with sanitized versions."""
        # Pattern for API keys (typically long alphanumeric strings)
        api_key_pattern = r"\b[A-Za-z0-9]{32,}\b"

        def replace_key(match):
            return self.get_replacement(match.group(0), "API_KEY")

        return re.sub(api_key_pattern, replace_key, text)

    def sanitize_user_ids(self, text: str) -> str:
        """Replace user IDs with sanitized versions."""
        # Pattern for UUIDs and similar IDs
        uuid_pattern = (
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        )

        def replace_uuid(match):
            return self.get_replacement(match.group(0), "USER_ID")

        return re.sub(uuid_pattern, replace_uuid, text, flags=re.IGNORECASE)

    def sanitize_conversation_ids(self, text: str) -> str:
        """Replace conversation IDs with sanitized versions."""
        # Pattern for conversation IDs (may be UUIDs or other formats)
        conv_id_pattern = r"\b(conv|conversation)[-_]?[0-9a-f]{8,}\b"

        def replace_conv_id(match):
            return self.get_replacement(match.group(0), "CONV_ID")

        return re.sub(conv_id_pattern, replace_conv_id, text, flags=re.IGNORECASE)

    def sanitize_emails(self, text: str) -> str:
        """Replace email addresses with sanitized versions."""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

        def replace_email(match):
            return self.get_replacement(match.group(0), "EMAIL")

        return re.sub(email_pattern, replace_email, text)

    def sanitize_urls(self, text: str) -> str:
        """Replace sensitive URLs while keeping API structure."""
        # Replace runtime URLs but keep the structure
        runtime_pattern = r"https://[a-zA-Z0-9-]+\.prod-runtime\.all-hands\.dev"
        text = re.sub(
            runtime_pattern, "https://RUNTIME_HOST.prod-runtime.all-hands.dev", text
        )

        # Replace workspace URLs
        workspace_pattern = r"https://[a-zA-Z0-9-]+\.workspace\.all-hands\.dev"
        text = re.sub(
            workspace_pattern, "https://WORKSPACE_HOST.workspace.all-hands.dev", text
        )

        return text

    def sanitize_timestamps(self, text: str) -> str:
        """Replace timestamps with consistent sanitized versions."""
        # ISO 8601 timestamps
        timestamp_pattern = (
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3,6})?(?:Z|[+-]\d{2}:\d{2})"
        )

        def replace_timestamp(match):
            return self.get_replacement(match.group(0), "TIMESTAMP")

        return re.sub(timestamp_pattern, replace_timestamp, text)

    def sanitize_json_recursively(self, data: Any) -> Any:
        """Recursively sanitize JSON data structures."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Sanitize keys that might contain sensitive info
                sanitized_key = key
                if key.lower() in ["api_key", "x-session-api-key", "authorization"]:
                    sanitized_key = key  # Keep the key name but sanitize the value

                sanitized[sanitized_key] = self.sanitize_json_recursively(value)
            return sanitized

        elif isinstance(data, list):
            return [self.sanitize_json_recursively(item) for item in data]

        elif isinstance(data, str):
            # Apply all sanitization rules to string values
            sanitized = data
            sanitized = self.sanitize_api_key(sanitized)
            sanitized = self.sanitize_user_ids(sanitized)
            sanitized = self.sanitize_conversation_ids(sanitized)
            sanitized = self.sanitize_emails(sanitized)
            sanitized = self.sanitize_urls(sanitized)
            sanitized = self.sanitize_timestamps(sanitized)
            return sanitized

        else:
            return data

    def sanitize_fixture(self, fixture_file: Path) -> None:
        """Sanitize a single fixture file."""
        print(f"Sanitizing: {fixture_file.name}")

        try:
            with open(fixture_file) as f:
                data = json.load(f)

            # Sanitize the data
            sanitized_data = self.sanitize_json_recursively(data)

            # Save sanitized version
            sanitized_file = self.sanitized_dir / fixture_file.name
            with open(sanitized_file, "w") as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False)

            print(f"  → {sanitized_file}")

        except Exception as e:
            print(f"  Error sanitizing {fixture_file}: {e}")

    def sanitize_all_fixtures(self) -> None:
        """Sanitize all fixture files in the directory."""
        print(f"Sanitizing v1 fixtures in: {self.fixtures_dir}")
        print(f"Output directory: {self.sanitized_dir}")

        fixture_files = list(self.fixtures_dir.glob("*.json"))
        if not fixture_files:
            print("No fixture files found to sanitize.")
            return

        for fixture_file in fixture_files:
            # Skip already sanitized files
            if fixture_file.parent.name == "sanitized":
                continue

            self.sanitize_fixture(fixture_file)

        # Save replacement mapping for reference
        mapping_file = self.sanitized_dir / "replacement_mapping.json"
        with open(mapping_file, "w") as f:
            json.dump(self.replacements, f, indent=2)

        print("\nSanitization complete!")
        print(f"Sanitized {len(fixture_files)} fixture files")
        print(f"Replacement mapping saved to: {mapping_file}")


def main():
    """Main function to run the sanitizer."""
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "v1"

    if not fixtures_dir.exists():
        print(f"Error: Fixtures directory not found: {fixtures_dir}")
        print("Please run record_api_responses.py first to create fixtures.")
        return

    sanitizer = V1FixtureSanitizer(fixtures_dir)
    sanitizer.sanitize_all_fixtures()


if __name__ == "__main__":
    main()
