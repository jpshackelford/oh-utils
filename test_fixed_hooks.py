#!/usr/bin/env python3
"""Test file to verify the fixed commit hooks work properly."""


def test_function():
    """A simple test function."""
    # This line is intentionally very long to exceed the 88 character limit and should trigger our comprehensive OpenHands pre-commit system
    return "This is a test"


if __name__ == "__main__":
    test_function()