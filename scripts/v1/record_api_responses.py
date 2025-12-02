#!/usr/bin/env python3
"""
Record OpenHands v1 API responses for integration testing.

This script records real API responses from the OpenHands v1 API endpoints
to create fixtures for testing. The responses are saved as JSON files
that can be used with the responses library for mocking HTTP requests.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class V1APIResponseRecorder:
    """Records OpenHands v1 API responses for testing fixtures."""

    def __init__(self, api_key: str, base_url: str = "https://app.all-hands.dev/api/"):
        """Initialize the recorder with API credentials."""
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
        )
        self.fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "v1"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def record_response(
        self,
        method: str,
        endpoint: str,
        filename: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single API response."""
        url = f"{self.base_url}{endpoint}"
        
        print(f"Recording {method} {url}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, params=params, json=json_data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Record the response data
            response_data = {
                "url": url,
                "method": method.upper(),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "params": params or {},
                "json_data": json_data,
            }
            
            # Try to parse JSON response
            try:
                response_data["json"] = response.json()
            except ValueError:
                response_data["text"] = response.text
            
            # Save to fixture file
            fixture_file = self.fixtures_dir / f"{filename}.json"
            with open(fixture_file, "w") as f:
                json.dump(response_data, f, indent=2, default=str)
            
            print(f"  Status: {response.status_code}")
            print(f"  Saved to: {fixture_file}")
            
        except Exception as e:
            print(f"  Error: {e}")
            # Save error response for testing error handling
            error_data = {
                "url": url,
                "method": method.upper(),
                "error": str(e),
                "params": params or {},
                "json_data": json_data,
            }
            
            fixture_file = self.fixtures_dir / f"{filename}_error.json"
            with open(fixture_file, "w") as f:
                json.dump(error_data, f, indent=2, default=str)
            
            print(f"  Error saved to: {fixture_file}")

    def record_all_endpoints(self) -> None:
        """Record responses from all v1 API endpoints."""
        print("Recording OpenHands v1 API responses...")
        
        # Test connection endpoint
        self.record_response("GET", "v1/events/count", "events_count_basic")
        
        # Events endpoints
        self.record_response(
            "GET", 
            "v1/events/search", 
            "events_search_basic",
            params={"limit": 10, "offset": 0}
        )
        
        self.record_response(
            "GET", 
            "v1/events/search", 
            "events_search_with_query",
            params={"query": "test", "limit": 5, "offset": 0}
        )
        
        self.record_response(
            "GET", 
            "v1/events/search", 
            "events_search_with_type",
            params={"event_type": "action", "limit": 10, "offset": 0}
        )
        
        self.record_response(
            "GET", 
            "v1/events/count", 
            "events_count_with_query",
            params={"query": "test"}
        )
        
        # App conversations endpoints
        self.record_response(
            "GET", 
            "v1/app-conversations/search", 
            "app_conversations_search_basic",
            params={"limit": 10, "offset": 0}
        )
        
        self.record_response(
            "GET", 
            "v1/app-conversations/search", 
            "app_conversations_search_with_query",
            params={"query": "test", "limit": 5, "offset": 0}
        )
        
        self.record_response(
            "GET", 
            "v1/app-conversations/count", 
            "app_conversations_count_basic"
        )
        
        self.record_response(
            "GET", 
            "v1/app-conversations/count", 
            "app_conversations_count_with_query",
            params={"query": "test"}
        )
        
        # Test unauthorized access (with invalid key)
        original_key = self.api_key
        self.session.headers.update({"X-Session-API-Key": "invalid_key"})
        
        self.record_response("GET", "v1/events/count", "events_count_unauthorized")
        self.record_response("GET", "v1/events/search", "events_search_unauthorized")
        self.record_response("GET", "v1/app-conversations/search", "app_conversations_search_unauthorized")
        
        # Restore original key
        self.session.headers.update({"X-Session-API-Key": original_key})
        
        print("\nRecording complete!")
        print(f"Fixtures saved to: {self.fixtures_dir}")


def main():
    """Main function to run the recorder."""
    api_key = os.getenv("OPENHANDS_API_KEY") or os.getenv("OH_API_KEY")
    if not api_key:
        print("Error: OPENHANDS_API_KEY or OH_API_KEY environment variable not set")
        print("Get your API key from: https://app.all-hands.dev/settings/api-keys")
        return
    
    base_url = os.getenv("OPENHANDS_BASE_URL", "https://app.all-hands.dev/api/")
    
    recorder = V1APIResponseRecorder(api_key, base_url)
    recorder.record_all_endpoints()


if __name__ == "__main__":
    main()