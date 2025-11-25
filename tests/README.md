# Integration Testing with API Fixtures

This directory contains integration tests for the OpenHands API client using recorded and sanitized API responses.

## Overview

The testing framework supports multiple approaches for testing HTTP interactions:

1. **Fixture-based testing** - Uses pre-recorded and sanitized API responses
2. **VCR.py integration** - Records and replays HTTP interactions automatically
3. **Responses library** - Simple HTTP mocking for unit tests

## Quick Start

### 1. Install Test Dependencies

```bash
# Install test dependencies
pip install -e ".[test]"

# Or using uv
uv pip install -e ".[test]"
```

### 2. Record API Fixtures

First, set your OpenHands API key:

```bash
export OPENHANDS_API_KEY=your_api_key_here
```

Then record and sanitize API responses:

```bash
# Record and sanitize in one step
python scripts/update_fixtures.py

# Or run steps separately
python scripts/record_api_responses.py
python scripts/sanitize_fixtures.py
```

### 3. Run Integration Tests

```bash
# Run all integration tests
pytest tests/test_api_integration.py -v

# Run with coverage
pytest tests/test_api_integration.py --cov=ohc --cov-report=html

# Run specific test
pytest tests/test_api_integration.py::TestOpenHandsAPIIntegration::test_search_conversations -v
```

## Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and fixtures
├── test_api_integration.py      # Integration tests using fixtures
├── vcr_config.py               # VCR.py configuration
├── fixtures/                   # Raw recorded API responses
│   ├── options_models.json
│   ├── conversations_list.json
│   └── ...
├── fixtures/sanitized/         # Sanitized fixtures for testing
│   ├── options_models.json
│   ├── conversations_list.json
│   ├── replacement_mapping.json
│   └── ...
└── cassettes/                  # VCR.py cassettes (if using VCR)
    └── ...
```

## Testing Approaches

### 1. Fixture-Based Testing (Recommended)

This approach uses pre-recorded API responses that have been sanitized to remove sensitive data.

**Pros:**
- Fast test execution
- No external dependencies during testing
- Consistent test results
- Safe for CI/CD (no real API keys needed)

**Cons:**
- Fixtures need to be updated when API changes
- May not catch all edge cases

**Example:**
```python
@responses.activate
def test_search_conversations(self, api_client, fixture_loader):
    fixture = fixture_loader.load("conversations_list")
    responses.add(
        responses.GET,
        "https://app.all-hands.dev/api/conversations",
        json=fixture["response"]["json"],
        status=fixture["response"]["status_code"]
    )
    
    result = api_client.search_conversations(limit=5)
    assert isinstance(result, dict)
```

### 2. VCR.py Integration

VCR.py automatically records HTTP interactions on first run and replays them on subsequent runs.

**Pros:**
- Automatic recording and replay
- More realistic than fixtures
- Good for exploratory testing

**Cons:**
- Requires real API access for initial recording
- Cassettes may contain sensitive data
- Slower than fixture-based tests

**Example:**
```python
@pytest.mark.vcr()
def test_with_vcr(self, api_client):
    # This will record the interaction on first run
    # and replay it on subsequent runs
    result = api_client.search_conversations()
    assert isinstance(result, dict)
```

### 3. Simple Mocking with Responses

For unit tests that need simple HTTP mocking without recorded data.

**Example:**
```python
@responses.activate
def test_simple_mock(self, api_client):
    responses.add(
        responses.GET,
        "https://app.all-hands.dev/api/conversations",
        json={"conversations": []},
        status=200
    )
    
    result = api_client.search_conversations()
    assert result == {"conversations": []}
```

## Updating Fixtures

When the OpenHands API changes, you'll need to update your fixtures:

```bash
# Update all fixtures
python scripts/update_fixtures.py

# Only record new responses (don't sanitize)
python scripts/update_fixtures.py --record-only

# Only sanitize existing fixtures
python scripts/update_fixtures.py --sanitize-only
```

## Fixture Sanitization

The sanitization process replaces sensitive data with fictitious data:

- **UUIDs** → `fake-uuid-12345678`
- **Runtime IDs** → `work-1-fakeworkspace001`
- **API Keys** → `sk-fakexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Session Keys** → `sess_fakexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Emails** → `user001@example.com`
- **Conversation Titles** → `Example Conversation 1`
- **URLs** → Sanitized versions maintaining structure

## Configuration

### Pytest Markers

The following pytest markers are available:

- `@pytest.mark.integration` - Mark tests as integration tests
- `@pytest.mark.vcr()` - Use VCR.py for HTTP recording/replay
- `@pytest.mark.slow` - Mark slow tests (can be skipped with `-m "not slow"`)

### Environment Variables

- `OPENHANDS_API_KEY` or `OH_API_KEY` - Your OpenHands API key
- `OPENHANDS_BASE_URL` - Custom base URL (default: https://app.all-hands.dev/api/)

## Best Practices

1. **Keep fixtures up to date** - Regularly update fixtures when the API changes
2. **Use descriptive test names** - Make it clear what each test is verifying
3. **Test error conditions** - Include tests for 4xx and 5xx responses
4. **Sanitize sensitive data** - Never commit real API keys or personal data
5. **Use appropriate test markers** - Mark integration tests appropriately
6. **Mock external dependencies** - Don't make real HTTP calls in unit tests

## Troubleshooting

### Fixture Not Found Error
```
FileNotFoundError: Fixture file not found: tests/fixtures/sanitized/some_fixture.json
```

**Solution:** Run the fixture recording script:
```bash
python scripts/update_fixtures.py
```

### API Key Error
```
Error: OPENHANDS_API_KEY or OH_API_KEY environment variable not set
```

**Solution:** Set your API key:
```bash
export OPENHANDS_API_KEY=your_api_key_here
```

### VCR Import Error
```
ImportError: No module named 'vcr'
```

**Solution:** Install VCR.py:
```bash
pip install vcrpy pytest-vcr
```

### Tests Failing After API Changes

**Solution:** Update your fixtures:
```bash
python scripts/update_fixtures.py
```

## Contributing

When adding new API endpoints or modifying existing ones:

1. Add the new endpoint to `record_api_responses.py`
2. Update the sanitization rules in `sanitize_fixtures.py` if needed
3. Add corresponding tests in `test_api_integration.py`
4. Update this README if necessary
5. Re-record fixtures: `python scripts/update_fixtures.py`