"""
Pytest configuration and fixtures for integration tests.

This module provides fixtures for loading sanitized API responses and
configuring HTTP mocking for integration tests.
"""

import json
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
import responses
from requests import Session

from ohc.api import OpenHandsAPI

# Try to import VCR.py components
try:
    from .vcr_config import default_vcr

    VCR_AVAILABLE = True
except ImportError:
    VCR_AVAILABLE = False


@pytest.fixture(autouse=True)
def restore_api_init():
    """Restore the original OpenHandsAPI.__init__ after each test.

    This prevents monkey-patching in interactive_mode() from affecting other tests.
    """
    original_init = OpenHandsAPI.__init__
    yield
    OpenHandsAPI.__init__ = original_init


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the sanitized fixtures directory."""
    return Path(__file__).parent / "fixtures" / "sanitized"


@pytest.fixture
def load_fixture():
    """Factory fixture to load a specific fixture file."""

    def _load_fixture(fixture_name: str, fixtures_dir: Path = None) -> Dict[str, Any]:
        if fixtures_dir is None:
            fixtures_dir = Path(__file__).parent / "fixtures" / "sanitized"

        fixture_file = fixtures_dir / f"{fixture_name}.json"
        if not fixture_file.exists():
            raise FileNotFoundError(f"Fixture file not found: {fixture_file}")

        with open(fixture_file) as f:
            return json.load(f)

    return _load_fixture


@pytest.fixture
def mock_responses() -> Generator[responses.RequestsMock, None, None]:
    """Provide a responses mock for HTTP requests."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def api_session() -> Session:
    """Create a requests session for API calls."""
    session = Session()
    session.headers.update(
        {"X-Session-API-Key": "fake-api-key", "Content-Type": "application/json"}
    )
    return session


@pytest.fixture
def mock_api_responses(mock_responses, load_fixture, fixtures_dir):
    """Set up mock responses for all API endpoints using fixtures."""

    def _setup_mocks():
        # Load and register all available fixtures
        fixture_files = list(fixtures_dir.glob("*.json"))

        for fixture_file in fixture_files:
            if fixture_file.name == "replacement_mapping.json":
                continue

            fixture_data = load_fixture(fixture_file.stem)
            request_data = fixture_data["request"]
            response_data = fixture_data["response"]

            # Register the mock response
            mock_responses.add(
                method=request_data["method"],
                url=request_data["url"],
                json=response_data.get("json"),
                body=response_data.get("content"),
                status=response_data["status_code"],
                headers=response_data.get("headers", {}),
            )

    return _setup_mocks


class FixtureLoader:
    """Helper class for loading and managing test fixtures."""

    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load(self, fixture_name: str) -> Dict[str, Any]:
        """Load a fixture by name, with caching."""
        if fixture_name not in self._cache:
            fixture_file = self.fixtures_dir / f"{fixture_name}.json"
            if not fixture_file.exists():
                raise FileNotFoundError(f"Fixture file not found: {fixture_file}")

            with open(fixture_file) as f:
                self._cache[fixture_name] = json.load(f)

        return self._cache[fixture_name]

    def get_response_json(self, fixture_name: str) -> Dict[str, Any]:
        """Get the JSON response data from a fixture."""
        fixture = self.load(fixture_name)
        return fixture["response"]["json"]

    def get_response_status(self, fixture_name: str) -> int:
        """Get the status code from a fixture."""
        fixture = self.load(fixture_name)
        return fixture["response"]["status_code"]


@pytest.fixture
def fixture_loader(fixtures_dir) -> FixtureLoader:
    """Provide a fixture loader instance."""
    return FixtureLoader(fixtures_dir)


# VCR.py integration
if VCR_AVAILABLE:

    @pytest.fixture
    def vcr_cassette_dir():
        """Return the directory for VCR cassettes."""
        return Path(__file__).parent / "cassettes"

    @pytest.fixture
    def vcr_config():
        """Return VCR configuration."""
        return {
            "record_mode": "once",
            "match_on": ["method", "uri", "body"],
            "filter_headers": ["X-Session-API-Key", "Authorization"],
            "decode_compressed_response": True,
        }

    # Enable pytest-vcr if available
    try:
        import pytest_vcr  # type: ignore[import-untyped]

        pytest_vcr.default_vcr = default_vcr
    except ImportError:
        pass
