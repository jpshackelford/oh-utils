#!/usr/bin/env python3
"""
Script to sanitize recorded API fixtures by replacing sensitive data with fictitious data.

This script processes the JSON fixtures created by record_api_responses.py and replaces
real data with fake data while maintaining the structure and data types.
"""

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Union


class FixtureSanitizer:
    """Sanitizes API response fixtures by replacing sensitive data."""

    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir
        self.sanitized_dir = fixtures_dir / "sanitized"
        self.sanitized_dir.mkdir(exist_ok=True)
        
        # Mapping to ensure consistent replacement of the same values
        self.replacements: Dict[str, str] = {}
        
        # Patterns for different types of sensitive data
        self.patterns = {
            "conversation_id": re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"),
            "runtime_id": re.compile(r"work-\d+-[a-z0-9]+"),
            "api_key": re.compile(r"sk-[a-zA-Z0-9]{32,}"),
            "session_key": re.compile(r"sess_[a-zA-Z0-9]{32,}"),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "url": re.compile(r"https?://[^\s/$.?#].[^\s]*"),
            "timestamp": re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
            "github_repo": re.compile(r"github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+"),
        }

    def generate_fake_data(self, data_type: str, original: str) -> str:
        """Generate consistent fake data for a given type and original value."""
        if original in self.replacements:
            return self.replacements[original]
        
        if data_type == "conversation_id":
            fake = str(uuid.uuid4())
        elif data_type == "runtime_id":
            fake = f"work-1-fakeworkspace{len(self.replacements):03d}"
        elif data_type == "api_key":
            fake = f"sk-fake{'x' * 32}"
        elif data_type == "session_key":
            fake = f"sess_fake{'x' * 32}"
        elif data_type == "email":
            username = f"user{len(self.replacements):03d}"
            fake = f"{username}@example.com"
        elif data_type == "url":
            if "prod-runtime.all-hands.dev" in original:
                # Handle both work-* and direct runtime ID patterns
                work_match = re.search(r"work-\d+-[a-z0-9]+", original)
                runtime_match = re.search(r"https://([a-z0-9]+)\.prod-runtime\.all-hands\.dev", original)
                
                if work_match:
                    fake = original.replace(
                        work_match.group(),
                        f"work-1-fakeworkspace{len(self.replacements):03d}"
                    )
                elif runtime_match:
                    fake = original.replace(
                        runtime_match.group(1),
                        f"fakeworkspace{len(self.replacements):03d}"
                    )
                else:
                    fake = f"https://fakeworkspace{len(self.replacements):03d}.prod-runtime.all-hands.dev/api/"
            elif "app.all-hands.dev" in original:
                fake = original  # Keep the base API URL
            else:
                fake = f"https://example.com/fake-url-{len(self.replacements):03d}"
        elif data_type == "timestamp":
            fake = "2024-01-15T10:30:00.000Z"
        elif data_type == "github_repo":
            fake = f"github.com/example-user/example-repo-{len(self.replacements):03d}"
        else:
            fake = f"fake-{data_type}-{len(self.replacements):03d}"
        
        self.replacements[original] = fake
        return fake

    def sanitize_string(self, text: str) -> str:
        """Sanitize a string by replacing sensitive patterns."""
        if not isinstance(text, str):
            return text
        
        result = text
        for data_type, pattern in self.patterns.items():
            matches = pattern.findall(result)
            for match in matches:
                fake = self.generate_fake_data(data_type, match)
                result = result.replace(match, fake)
        
        return result

    def sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize any value (string, dict, list, etc.)."""
        if isinstance(value, str):
            return self.sanitize_string(value)
        elif isinstance(value, dict):
            return {k: self.sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.sanitize_value(item) for item in value]
        else:
            return value

    def sanitize_fixture(self, fixture_file: Path) -> None:
        """Sanitize a single fixture file."""
        print(f"Sanitizing {fixture_file.name}...")
        
        # Check file size - skip very large files (likely binary content)
        file_size = fixture_file.stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB threshold
            print(f"  Skipping large file ({file_size / (1024*1024):.1f}MB) - likely binary content")
            # Just copy the file without sanitization
            output_file = self.sanitized_dir / fixture_file.name
            import shutil
            shutil.copy2(fixture_file, output_file)
            return
        
        try:
            with open(fixture_file, "r") as f:
                data = json.load(f)
            
            # Sanitize the entire fixture
            sanitized_data = self.sanitize_value(data)
            
            # Additional specific sanitizations
            if "response" in sanitized_data and "json" in sanitized_data["response"]:
                response_json = sanitized_data["response"]["json"]
                
                # Sanitize conversation titles to be more generic
                if isinstance(response_json, dict):
                    if "conversations" in response_json:
                        for i, conv in enumerate(response_json["conversations"]):
                            if "title" in conv:
                                conv["title"] = f"Example Conversation {i + 1}"
                    elif "title" in response_json:
                        response_json["title"] = "Example Conversation"
                    
                    # Sanitize user names and other personal info
                    if "user" in response_json:
                        if isinstance(response_json["user"], dict):
                            response_json["user"]["name"] = "Example User"
                            response_json["user"]["username"] = "example_user"
            
            # Update the response content to match the sanitized JSON
            if ("response" in sanitized_data and 
                "json" in sanitized_data["response"] and 
                sanitized_data["response"]["json"]):
                sanitized_data["response"]["content"] = json.dumps(
                    sanitized_data["response"]["json"], 
                    separators=(',', ':')
                )
            
            # Save sanitized fixture
            output_file = self.sanitized_dir / fixture_file.name
            with open(output_file, "w") as f:
                json.dump(sanitized_data, f, indent=2)
            
            print(f"✓ Saved sanitized version to {output_file}")
            
        except Exception as e:
            print(f"✗ Failed to sanitize {fixture_file.name}: {e}")

    def sanitize_all_fixtures(self) -> None:
        """Sanitize all fixture files in the fixtures directory."""
        print("Sanitizing API response fixtures...")
        print(f"Input directory: {self.fixtures_dir}")
        print(f"Output directory: {self.sanitized_dir}")
        print("-" * 50)
        
        fixture_files = list(self.fixtures_dir.glob("*.json"))
        if not fixture_files:
            print("No fixture files found to sanitize.")
            return
        
        for fixture_file in fixture_files:
            # Skip already sanitized files
            if fixture_file.parent.name == "sanitized":
                continue
            self.sanitize_fixture(fixture_file)
        
        print("-" * 50)
        print(f"Sanitization complete! {len(fixture_files)} files processed.")
        print(f"Sanitized fixtures saved in: {self.sanitized_dir}")
        
        # Save replacement mapping for reference
        mapping_file = self.sanitized_dir / "replacement_mapping.json"
        with open(mapping_file, "w") as f:
            json.dump(self.replacements, f, indent=2)
        print(f"Replacement mapping saved to: {mapping_file}")


def main():
    """Main function to run the sanitizer."""
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    
    if not fixtures_dir.exists():
        print(f"Error: Fixtures directory not found: {fixtures_dir}")
        print("Please run record_api_responses.py first to create fixtures.")
        return
    
    sanitizer = FixtureSanitizer(fixtures_dir)
    sanitizer.sanitize_all_fixtures()


if __name__ == "__main__":
    main()