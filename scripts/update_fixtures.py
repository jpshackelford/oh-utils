#!/usr/bin/env python3
"""
Master script to update API fixtures.

This script combines the recording and sanitization process into a single
workflow for updating test fixtures when the API changes.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the other scripts
sys.path.insert(0, str(Path(__file__).parent))

from record_api_responses import APIResponseRecorder
from sanitize_fixtures import FixtureSanitizer


def main():
    """Main function to orchestrate fixture updates."""
    parser = argparse.ArgumentParser(
        description="Update API test fixtures by recording and sanitizing responses"
    )
    parser.add_argument(
        "--record-only",
        action="store_true",
        help="Only record responses, don't sanitize",
    )
    parser.add_argument(
        "--sanitize-only",
        action="store_true",
        help="Only sanitize existing fixtures, don't record new ones",
    )
    parser.add_argument(
        "--api-key", help="OpenHands API key (overrides environment variables)"
    )
    parser.add_argument(
        "--base-url",
        default="https://app.all-hands.dev/api/",
        help="Base URL for the OpenHands API",
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("OPENHANDS_API_KEY") or os.getenv("OH_API_KEY")
    if not api_key and not args.sanitize_only:
        print("Error: API key required for recording")
        print("Set OPENHANDS_API_KEY environment variable or use --api-key")
        sys.exit(1)

    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"

    # Record new responses
    if not args.sanitize_only:
        print("=" * 60)
        print("STEP 1: Recording API responses")
        print("=" * 60)

        recorder = APIResponseRecorder(api_key, args.base_url)
        recorder.record_all_endpoints()

        if args.record_only:
            print("\nRecording complete. Use --sanitize-only to sanitize the fixtures.")
            return

    # Sanitize fixtures
    if not args.record_only:
        print("\n" + "=" * 60)
        print("STEP 2: Sanitizing fixtures")
        print("=" * 60)

        if not fixtures_dir.exists():
            print(f"Error: Fixtures directory not found: {fixtures_dir}")
            print("Run with recording enabled first.")
            sys.exit(1)

        sanitizer = FixtureSanitizer(fixtures_dir)
        sanitizer.sanitize_all_fixtures()

    print("\n" + "=" * 60)
    print("FIXTURE UPDATE COMPLETE")
    print("=" * 60)
    print(f"Fixtures location: {fixtures_dir}")
    print(f"Sanitized fixtures: {fixtures_dir / 'sanitized'}")
    print("\nYou can now run integration tests with:")
    print("  pytest tests/test_api_integration.py -v")


if __name__ == "__main__":
    main()
