#!/usr/bin/env python3
"""
OpenHands Conversation Downloader

A utility to download conversations and their workspace files from OpenHands Cloud API.
"""

import os
import sys
import json
import zipfile
import base64
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any


API_BASE_URL = "https://app.all-hands.dev"
CONFIG_DIR = Path.home() / ".config" / "openhands"
TOKEN_FILE = CONFIG_DIR / "api_token"


class OpenHandsAPI:
    """Client for interacting with OpenHands Cloud API."""
    
    def __init__(self, api_token: str, user_id: Optional[str] = None):
        self.api_token = api_token
        self.user_id = user_id
        self.headers = {
            "X-Session-API-Key": api_token
        }
        
        # Setup simple session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def test_connection(self) -> bool:
        """Test if the API token is valid."""
        try:
            response = self.session.get(
                f"{API_BASE_URL}/api/conversations",
                params={"limit": 1},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def list_conversations(self, limit: int = 100, next_page_id: Optional[str] = None) -> Dict[str, Any]:
        """List conversations with pagination."""
        params = {"limit": min(limit, 100)}
        if next_page_id:
            params["next_page_id"] = next_page_id
            
        response = self.session.get(
            f"{API_BASE_URL}/api/conversations",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation metadata including runtime URL and session key."""
        response = self.session.get(
            f"{API_BASE_URL}/api/conversations/{conversation_id}",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def list_workspace_files(self, runtime_url: str, session_key: str, path: str = "/workspace/project") -> List[str]:
        """List files in workspace using runtime API."""
        headers = {"X-Session-API-Key": session_key}
        response = self.session.get(
            f"{runtime_url}/list-files",
            headers=headers,
            params={"path": path},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_file_content(self, runtime_url: str, session_key: str, file_path: str) -> str:
        """Get file content from workspace using runtime API."""
        headers = {"X-Session-API-Key": session_key}
        response = self.session.get(
            f"{runtime_url}/select-file",
            headers=headers,
            params={"file": file_path},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get('code', '')


def load_token() -> Optional[str]:
    """Load API token from config file."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None


def save_token(token: str) -> None:
    """Save API token to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)  # Make file readable only by owner


def get_api_token() -> str:
    """Get API token, prompting user if necessary."""
    token = load_token()
    
    if token:
        # Test if existing token works
        api = OpenHandsAPI(token)
        if api.test_connection():
            print("Using existing API token.")
            return token
        else:
            print("Existing API token is invalid or expired.")
    
    # Prompt for new token
    print("\nPlease enter your OpenHands API token.")
    print("Get your token from: https://app.all-hands.dev/settings/api-keys")
    token = input("API Token: ").strip()
    
    if not token:
        print("Error: No token provided.")
        sys.exit(1)
    
    # Test the new token
    api = OpenHandsAPI(token)
    if not api.test_connection():
        print("Error: Invalid API token.")
        sys.exit(1)
    
    # Save the token
    save_token(token)
    print("API token saved successfully.")
    
    return token


def format_filename(title: str, max_length: int = 30, suffix: str = "") -> str:
    """Format a conversation title into a valid filename."""
    # Convert to lowercase and replace spaces with dashes
    filename = title.lower().replace(' ', '-')
    
    # Remove special characters
    filename = ''.join(c for c in filename if c.isalnum() or c == '-')
    
    # Remove consecutive dashes
    while '--' in filename:
        filename = filename.replace('--', '-')
    
    # Trim to max length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('-')
    
    # Add suffix if provided
    if suffix:
        filename = f"{filename}{suffix}"
    
    return filename


def display_conversations(api: OpenHandsAPI, max_pages: int = 10) -> List[Dict[str, Any]]:
    """Display list of conversations with pagination."""
    all_conversations = []
    next_page_id = None
    limit = 20  # Smaller page size to avoid rate limits
    page_count = 0
    
    print("\nFetching conversations...\n")
    
    while page_count < max_pages:
        try:
            result = api.list_conversations(limit=limit, next_page_id=next_page_id)
            conversations = result.get('results', [])
            
            if not conversations:
                break
            
            all_conversations.extend(conversations)
            page_count += 1
            
            # Check if there are more pages
            next_page_id = result.get('next_page_id')
            if not next_page_id:
                break
                
            # Small delay to avoid rate limits
            import time
            time.sleep(0.5)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"\n⚠️  Hit rate limit. Showing {len(all_conversations)} conversations so far.")
                break
            else:
                raise
    
    # Display conversations
    print(f"Found {len(all_conversations)} conversation(s):\n")
    for i, conv in enumerate(all_conversations, 1):
        title = conv.get('title', 'Untitled')
        conv_id = conv.get('conversation_id', 'unknown')
        created = conv.get('created_at', 'unknown')
        updated = conv.get('last_updated_at', 'unknown')
        status = conv.get('status', 'unknown')
        
        print(f"{i}. {title}")
        print(f"   ID: {conv_id} | Status: {status}")
        print(f"   Created: {created}")
        print(f"   Updated: {updated}")
        print()
    
    return all_conversations


def select_conversation(conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prompt user to select a conversation."""
    while True:
        try:
            selection = input(f"Select a conversation (1-{len(conversations)}): ").strip()
            index = int(selection) - 1
            
            if 0 <= index < len(conversations):
                return conversations[index]
            else:
                print(f"Please enter a number between 1 and {len(conversations)}.")
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)


def collect_all_files(api: OpenHandsAPI, runtime_url: str, session_key: str, path: str, all_files: List[str]) -> None:
    """Recursively collect all files from workspace."""
    try:
        items = api.list_workspace_files(runtime_url, session_key, path)
        for item in items:
            if item.endswith('/'):
                # It's a directory, recurse into it
                collect_all_files(api, runtime_url, session_key, item.rstrip('/'), all_files)
            else:
                # It's a file
                all_files.append(item)
    except Exception as e:
        print(f"  Warning: Could not list {path}: {e}")


def download_workspace(api: OpenHandsAPI, conversation: Dict[str, Any]) -> None:
    """Download full workspace as archive including all files and metadata."""
    conv_id = conversation.get('conversation_id')
    title = conversation.get('title', 'untitled')
    runtime_url = conversation.get('url')
    session_key = conversation.get('session_api_key')
    
    if not runtime_url or not session_key:
        print("\n✗ No runtime URL or session key found. Conversation may not be active.")
        return
    
    filename = format_filename(title) + ".zip"
    output_path = Path.cwd() / filename
    
    print(f"\nCollecting files from workspace...")
    
    # Collect all files from /workspace/project
    all_files = []
    collect_all_files(api, runtime_url, session_key, "/workspace/project", all_files)
    
    if not all_files:
        print("\n✗ No files found in workspace.")
        return
    
    print(f"Found {len(all_files)} file(s)")
    print(f"\nCreating workspace archive: {filename}")
    
    # Create temporary directory for extraction
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save conversation metadata
        metadata_path = temp_path / "conversation_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                'conversation_id': conv_id,
                'title': title,
                'created_at': conversation.get('created_at'),
                'last_updated_at': conversation.get('last_updated_at'),
                'status': conversation.get('status'),
                'num_files': len(all_files)
            }, f, indent=2)
        
        # Download each file
        for i, file_path in enumerate(all_files, 1):
            # Remove /workspace/project prefix for display
            display_path = file_path.replace('/workspace/project/', '')
            print(f"  [{i}/{len(all_files)}] {display_path}")
            
            try:
                content = api.get_file_content(runtime_url, session_key, file_path)
                
                # Save relative to temp directory
                rel_path = file_path.replace('/workspace/project/', '')
                output_file = temp_path / rel_path
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(content)
            except Exception as e:
                print(f"    ✗ Error: {e}")
                continue
        
        # Create zip archive
        print(f"\nCompressing archive...")
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_path)
                    zipf.write(file_path, arcname)
    
    file_size = output_path.stat().st_size
    print(f"✓ Archive created: {output_path} ({file_size:,} bytes)")


def download_changed_files(api: OpenHandsAPI, conversation: Dict[str, Any]) -> None:
    """Download workspace files with '-changes' suffix (for Cloud API, downloads all workspace files)."""
    conv_id = conversation.get('conversation_id')
    title = conversation.get('title', 'untitled')
    runtime_url = conversation.get('url')
    session_key = conversation.get('session_api_key')
    
    if not runtime_url or not session_key:
        print("\n✗ No runtime URL or session key found. Conversation may not be active.")
        return
    
    # Create temporary directory
    dir_name = format_filename(title, suffix="-changes")
    temp_dir = Path("/tmp") / dir_name
    
    # Clean up if exists
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    print(f"\nCollecting files from workspace...")
    
    # Collect all files from /workspace/project
    all_files = []
    collect_all_files(api, runtime_url, session_key, "/workspace/project", all_files)
    
    if not all_files:
        print("\n✗ No files found in workspace.")
        return
    
    print(f"Found {len(all_files)} file(s)")
    
    # Show preview
    print("\nFirst few files:")
    for i, file_path in enumerate(all_files[:3], 1):
        display_path = file_path.replace('/workspace/project/', '')
        print(f"  {i}. {display_path}")
    if len(all_files) > 3:
        print(f"  ... and {len(all_files) - 3} more")
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownloading files...")
    
    # Download each file
    for i, file_path in enumerate(all_files, 1):
        display_path = file_path.replace('/workspace/project/', '')
        print(f"  [{i}/{len(all_files)}] {display_path}")
        
        try:
            content = api.get_file_content(runtime_url, session_key, file_path)
            
            # Save relative to temp directory
            rel_path = file_path.replace('/workspace/project/', '')
            output_file = temp_dir / rel_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content)
        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue
    
    # Create zip archive
    zip_filename = dir_name + ".zip"
    zip_path = Path.cwd() / zip_filename
    
    print(f"\nCreating archive: {zip_filename}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in temp_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_dir)
                zipf.write(file_path, arcname)
    
    file_size = zip_path.stat().st_size
    print(f"✓ Archive created: {zip_path} ({file_size:,} bytes)")
    
    # Clean up temp directory
    shutil.rmtree(temp_dir)


def main():
    """Main entry point."""
    print("=" * 60)
    print("OpenHands Conversation Downloader (Cloud API)")
    print("=" * 60)
    
    # Get API token
    token = get_api_token()
    
    # Optionally get user ID for filtering
    user_id = os.getenv('OPENHANDS_USER_ID')
    if user_id:
        print(f"Filtering conversations for user: {user_id}")
    
    api = OpenHandsAPI(token, user_id=user_id)
    
    # Display conversations
    try:
        conversations = display_conversations(api)
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        sys.exit(1)
    
    if not conversations:
        print("No conversations found.")
        sys.exit(0)
    
    # Select conversation
    conversation = select_conversation(conversations)
    title = conversation.get('title', 'Untitled')
    status = conversation.get('status', 'UNKNOWN')
    
    print(f"\nSelected: {title}")
    print(f"Status: {status}")
    
    # Check if conversation is active
    if status not in ['RUNNING', 'STOPPED']:
        print(f"\n⚠️  Warning: Conversation status is '{status}'")
        print("   Files may not be accessible if conversation is not active.")
        proceed = input("\nProceed anyway? (y/N): ").strip().lower()
        if proceed != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    print("\nWhat would you like to download?")
    print("1. Workspace archive (full workspace as ZIP)")
    print("2. Files archive with '-changes' suffix")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice == "1":
            download_workspace(api, conversation)
            break
        elif choice == "2":
            download_changed_files(api, conversation)
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
