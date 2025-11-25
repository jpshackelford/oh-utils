#!/usr/bin/env python3
"""
Script to record actual API responses from OpenHands API for testing fixtures.

This script uses the OpenHands API to capture real responses and save them
as JSON files that can be used as test fixtures after sanitization.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class APIResponseRecorder:
    """Records API responses for fixture generation."""

    def __init__(self, api_key: str, base_url: str = "https://app.all-hands.dev/api/"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Session-API-Key": api_key,
            "Content-Type": "application/json"
        })
        self.fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def record_response(self, method: str, endpoint: str, filename: str, 
                       params: Optional[Dict[str, Any]] = None,
                       json_data: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None) -> bool:
        """Record a single API response."""
        url = self.base_url + endpoint.lstrip("/")
        
        try:
            print(f"Recording {method} {endpoint}...")
            
            # Merge additional headers if provided
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=request_headers)
            elif method.upper() == "POST":
                response = self.session.post(url, params=params, json=json_data, headers=request_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Create fixture data
            fixture_data = {
                "request": {
                    "method": method.upper(),
                    "url": url,
                    "params": params,
                    "json": json_data,
                    "headers": dict(request_headers)
                },
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text,
                    "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                }
            }
            
            # Save to file
            fixture_file = self.fixtures_dir / f"{filename}.json"
            with open(fixture_file, "w") as f:
                json.dump(fixture_data, f, indent=2, default=str)
            
            print(f"✓ Saved to {fixture_file}")
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to record {method} {endpoint}: {e}")
            return False

    def record_all_endpoints(self) -> None:
        """Record responses from all known API endpoints."""
        print("Recording API responses for test fixtures...")
        print(f"Base URL: {self.base_url}")
        print(f"Fixtures directory: {self.fixtures_dir}")
        print("-" * 50)
        
        # Test connection endpoint
        self.record_response("GET", "options/models", "options_models")
        
        # Get conversations list
        self.record_response("GET", "conversations", "conversations_list", 
                           params={"limit": 5})
        
        # Get conversations with pagination
        self.record_response("GET", "conversations", "conversations_list_paginated",
                           params={"limit": 2})
        
        # Try to get a specific conversation (this might fail if no conversations exist)
        # First, let's get the conversation list to find a real conversation ID
        try:
            response = self.session.get(self.base_url + "conversations", params={"limit": 1})
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("results", [])
                if conversations:
                    conversation_id = conversations[0]["conversation_id"]
                    print(f"Found conversation ID: {conversation_id}")
                    
                    # Record conversation details
                    self.record_response("GET", f"conversations/{conversation_id}", 
                                       "conversation_details")
                    
                    # Get conversation details to find runtime_id and session_api_key
                    conv_response = self.session.get(f"{self.base_url}conversations/{conversation_id}")
                    if conv_response.status_code == 200:
                        conv_details = conv_response.json()
                        runtime_id = conv_details.get("runtime_id")
                        session_api_key = conv_details.get("session_api_key")
                        
                        # If no runtime_id, try to extract from URL
                        if not runtime_id:
                            url = conv_details.get("url", "")
                            if url and "prod-runtime.all-hands.dev" in url:
                                # Extract runtime ID from URL like https://bqeiqcnuedgsqjuo.prod-runtime.all-hands.dev/api/...
                                import re
                                match = re.search(r'https://([^.]+)\.prod-runtime\.all-hands\.dev', url)
                                if match:
                                    runtime_id = match.group(1)
                        
                        if runtime_id:
                            print(f"Found runtime ID: {runtime_id}")
                            if session_api_key:
                                print(f"Found session API key: {session_api_key[:10]}...")
                            else:
                                print("No session API key found in conversation details")
                            
                            # Try to start the conversation (may update session state)
                            print("Attempting to start conversation...")
                            start_response = self.session.post(
                                f"{self.base_url}conversations/{conversation_id}/start",
                                json={"providers_set": ["github"]}
                            )
                            
                            # Record the start response regardless of success
                            self.record_response("POST", f"conversations/{conversation_id}/start",
                                               "conversation_start", 
                                               json_data={"providers_set": ["github"]})
                            
                            # Record runtime endpoints (try both with session key and fallback auth)
                            runtime_base = f"https://{runtime_id}.prod-runtime.all-hands.dev/api/"
                            
                            # Prepare headers - try session key first, then fallback to Bearer token
                            runtime_headers = {}
                            if session_api_key:
                                runtime_headers["X-Session-API-Key"] = session_api_key
                            else:
                                runtime_headers["Authorization"] = f"Bearer {self.api_key}"
                                print("Using Bearer token fallback for runtime API")
                            
                            # Create a separate recorder for runtime API
                            runtime_recorder = APIResponseRecorder(self.api_key, runtime_base)
                            
                            # Record runtime endpoints
                            print("Recording runtime API endpoints...")
                            runtime_recorder.record_response("GET", 
                                                            f"conversations/{conversation_id}/git/changes",
                                                            "git_changes",
                                                            headers=runtime_headers)
                            
                            runtime_recorder.record_response("GET",
                                                            f"conversations/{conversation_id}/trajectory", 
                                                            "trajectory",
                                                            headers=runtime_headers)
                            
                            # File content endpoint - try a common file first
                            runtime_recorder.record_response("GET",
                                                            f"conversations/{conversation_id}/select-file",
                                                            "select_file_readme",
                                                            params={"file": "README.md"},
                                                            headers=runtime_headers)
                            
                            # Also try a non-existent file to get 404 response
                            runtime_recorder.record_response("GET",
                                                            f"conversations/{conversation_id}/select-file",
                                                            "select_file_not_found",
                                                            params={"file": "nonexistent.txt"},
                                                            headers=runtime_headers)
                            
                            # Try workspace archive download
                            runtime_recorder.record_response("GET",
                                                            f"conversations/{conversation_id}/zip-directory",
                                                            "workspace_archive",
                                                            headers=runtime_headers)
                        else:
                            print("No runtime_id found - conversation may not be active")
                    else:
                        print(f"Failed to get conversation details: {conv_response.status_code}")
                else:
                    print("No conversations found - skipping conversation-specific endpoints")
            else:
                print(f"Failed to get conversations list: {response.status_code}")
                
        except Exception as e:
            print(f"Error while recording conversation-specific endpoints: {e}")
        
        print("-" * 50)
        print("Recording complete!")
        print(f"Fixtures saved in: {self.fixtures_dir}")


def main():
    """Main function to run the recorder."""
    api_key = os.getenv("OH_API_KEY") or os.getenv("OPENHANDS_API_KEY")
    
    if not api_key:
        print("Error: OPENHANDS_API_KEY or OH_API_KEY environment variable not set")
        print("Please set your OpenHands API key:")
        print("  export OPENHANDS_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # Allow custom base URL via environment variable
    base_url = os.getenv("OPENHANDS_BASE_URL", "https://app.all-hands.dev/api/")
    
    recorder = APIResponseRecorder(api_key, base_url)
    recorder.record_all_endpoints()


if __name__ == "__main__":
    main()