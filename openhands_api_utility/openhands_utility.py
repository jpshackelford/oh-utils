#!/usr/bin/env python3
"""
OpenHands API Utility

A utility to interact with the OpenHands API to:
- Manage API keys
- List conversations with pagination
- Download workspace archives or changed files
"""

import os
import sys
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from urllib.parse import urljoin


class OpenHandsAPI:
    """OpenHands API client"""
    
    BASE_URL = "https://app.all-hands.dev/api/"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Session-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test if the API key is valid"""
        try:
            response = self.session.get(urljoin(self.BASE_URL, "options/models"))
            return response.status_code == 200
        except Exception:
            return False
    
    def search_conversations(self, page_id: Optional[str] = None, limit: int = 20) -> Dict:
        """Search conversations with pagination"""
        url = urljoin(self.BASE_URL, "conversations")
        params = {"limit": limit}
        if page_id:
            params["page_id"] = page_id
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception(
                    "API key does not have permission to access conversations. "
                    "Please ensure you're using a full API key from https://app.all-hands.dev/settings/api-keys "
                    "rather than a session-specific key."
                )
            raise
    
    def get_git_changes(self, conversation_id: str) -> Dict:
        """Get git changes for a conversation"""
        url = urljoin(self.BASE_URL, f"conversations/{conversation_id}/git/changes")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_trajectory(self, conversation_id: str, runtime_id: str, session_api_key: str) -> Dict:
        """Get trajectory data from runtime URL"""
        # Use runtime URL pattern for trajectory data
        runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
        url = f"{runtime_url}/api/conversations/{conversation_id}/trajectory"
        
        headers = {'X-Session-API-Key': session_api_key}
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def download_workspace_archive(self, conversation_id: str, runtime_id: str, session_api_key: str) -> bytes:
        """Download workspace archive as zip from runtime URL"""
        # Use runtime URL pattern for workspace downloads
        runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
        url = f"{runtime_url}/api/conversations/{conversation_id}/zip-directory"
        
        headers = {'X-Session-API-Key': session_api_key}
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    
    def get_file_content(self, conversation_id: str, file_path: str) -> bytes:
        """Get content of a specific file"""
        url = urljoin(self.BASE_URL, f"conversations/{conversation_id}/select-file")
        params = {"file": file_path}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.content


class APIKeyManager:
    """Manages OpenHands API key storage and retrieval"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".openhands"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
    
    def get_stored_key(self) -> Optional[str]:
        """Get stored API key if it exists"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('api_key')
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def store_key(self, api_key: str) -> None:
        """Store API key securely"""
        config = {'api_key': api_key}
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        # Set restrictive permissions
        os.chmod(self.config_file, 0o600)
    
    def get_valid_key(self) -> str:
        """Get a valid API key, prompting user if necessary"""
        # Check if stored key exists and works
        stored_key = self.get_stored_key()
        if stored_key:
            api = OpenHandsAPI(stored_key)
            if api.test_connection():
                # Test conversations access to verify it's a full API key
                try:
                    api.search_conversations(limit=1)
                    print("✓ Using stored API key")
                    return stored_key
                except Exception as e:
                    if "API key does not have permission" in str(e):
                        print("⚠ Stored API key is a session key, not a full API key")
                        print("  Please get a full API key from: https://app.all-hands.dev/settings/api-keys")
                    else:
                        print(f"⚠ Error testing conversations access: {e}")
            else:
                print("⚠ Stored API key is invalid")
        
        # Prompt for new key
        print("\nPlease get your OpenHands API key from:")
        print("https://app.all-hands.dev/settings/api-keys")
        print()
        
        while True:
            try:
                api_key = input("Enter your OpenHands API key: ").strip()
                if not api_key:
                    print("API key cannot be empty")
                    continue
                
                api = OpenHandsAPI(api_key)
                if api.test_connection():
                    # Test conversations access to verify it's a full API key
                    try:
                        api.search_conversations(limit=1)
                        self.store_key(api_key)
                        print("✓ API key validated and stored")
                        return api_key
                    except Exception as e:
                        if "API key does not have permission" in str(e):
                            print("✗ This appears to be a session key, not a full API key")
                            print("  Please get a full API key from: https://app.all-hands.dev/settings/api-keys")
                        else:
                            print(f"✗ Error testing conversations access: {e}")
                else:
                    print("✗ Invalid API key, please try again")
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user")
                sys.exit(0)
            except EOFError:
                print("\n\nNo input provided")
                sys.exit(1)


def format_filename(title: str, max_length: int = 30) -> str:
    """Format conversation title for filename"""
    # Convert to lowercase and replace spaces with dashes
    filename = title.lower().replace(' ', '-')
    # Remove special characters
    filename = ''.join(c for c in filename if c.isalnum() or c in '-_')
    # Remove multiple consecutive dashes
    while '--' in filename:
        filename = filename.replace('--', '-')
    # Remove leading/trailing dashes
    filename = filename.strip('-_')
    # Truncate to max length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('-_')
    return filename


def display_conversations(conversations: List[Dict], start_index: int = 0) -> None:
    """Display conversations in a numbered list"""
    print("\nRecent Conversations:")
    print("-" * 80)
    
    for i, conv in enumerate(conversations, start_index + 1):
        title = conv.get('title', 'Untitled')
        status = conv.get('status', 'Unknown')
        last_updated = conv.get('last_updated_at', 'Unknown')
        repo = conv.get('selected_repository', 'No repository')
        
        print(f"{i:2d}. {title}")
        print(f"    Status: {status} | Repository: {repo}")
        print(f"    Last updated: {last_updated}")
        print()


def get_user_choice(max_choice: int) -> int:
    """Get user's conversation choice"""
    while True:
        try:
            choice = input(f"Select conversation (1-{max_choice}): ").strip()
            if not choice:
                continue
            choice_num = int(choice)
            if 1 <= choice_num <= max_choice:
                return choice_num - 1  # Convert to 0-based index
            else:
                print(f"Please enter a number between 1 and {max_choice}")
        except ValueError:
            print("Please enter a valid number")


def download_changed_files(api: OpenHandsAPI, conversation_id: str, 
                         conversation_title: str, changed_files: List[str]) -> str:
    """Download changed files to a temporary directory and zip them"""
    base_name = format_filename(conversation_title)
    temp_dir_name = f"{base_name}-changes"
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_base:
        temp_dir = Path(temp_base) / temp_dir_name
        temp_dir.mkdir()
        
        print(f"\nDownloading {len(changed_files)} changed files...")
        
        for i, file_path in enumerate(changed_files, 1):
            try:
                print(f"  [{i}/{len(changed_files)}] {file_path}")
                
                # Get file content
                content = api.get_file_content(conversation_id, file_path)
                
                # Create directory structure
                file_dest = temp_dir / file_path.lstrip('/')
                file_dest.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                with open(file_dest, 'wb') as f:
                    f.write(content)
                    
            except Exception as e:
                print(f"    ⚠ Failed to download {file_path}: {e}")
        
        # Create zip file
        zip_path = Path.cwd() / f"{temp_dir_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
        
        return str(zip_path)


def main():
    """Main function"""
    print("OpenHands API Utility")
    print("=" * 50)
    
    # Get valid API key
    key_manager = APIKeyManager()
    api_key = key_manager.get_valid_key()
    api = OpenHandsAPI(api_key)
    
    # Get conversations with pagination
    all_conversations = []
    page_id = None
    
    print("\nFetching conversations...")
    while True:
        try:
            result = api.search_conversations(page_id=page_id, limit=50)
            conversations = result.get('results', [])
            all_conversations.extend(conversations)
            
            page_id = result.get('next_page_id')
            if not page_id or not conversations:
                break
                
            print(f"  Fetched {len(all_conversations)} conversations so far...")
            
        except Exception as e:
            print(f"Error fetching conversations: {e}")
            return 1
    
    if not all_conversations:
        print("No conversations found.")
        return 0
    
    print(f"Found {len(all_conversations)} conversations total.")
    
    # Display conversations in pages
    page_size = 20
    current_page = 0
    
    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(all_conversations))
        page_conversations = all_conversations[start_idx:end_idx]
        
        display_conversations(page_conversations, start_idx)
        
        # Show pagination info
        total_pages = (len(all_conversations) + page_size - 1) // page_size
        print(f"Page {current_page + 1} of {total_pages}")
        
        if total_pages > 1:
            print("Commands: [n]ext page, [p]revious page, [number] to select conversation, [q]uit")
        else:
            print("Commands: [number] to select conversation, [q]uit")
        
        choice = input("Enter choice: ").strip().lower()
        
        if choice == 'q':
            return 0
        elif choice == 'n' and current_page < total_pages - 1:
            current_page += 1
            continue
        elif choice == 'p' and current_page > 0:
            current_page -= 1
            continue
        elif choice.isdigit():
            try:
                conv_idx = int(choice) - 1
                if 0 <= conv_idx < len(all_conversations):
                    selected_conversation = all_conversations[conv_idx]
                    break
                else:
                    print("Invalid conversation number")
                    continue
            except ValueError:
                print("Invalid input")
                continue
        else:
            print("Invalid command")
            continue
    
    # Process selected conversation
    conv_id = selected_conversation['conversation_id']
    conv_title = selected_conversation.get('title', 'Untitled')
    
    print(f"\nSelected: {conv_title}")
    
    # Get changed files
    try:
        changes = api.get_git_changes(conv_id)
        changed_files = list(changes.keys()) if isinstance(changes, dict) else []
    except Exception as e:
        print(f"Warning: Could not fetch changed files: {e}")
        changed_files = []
    
    # Ask user what to download
    print(f"\nOptions:")
    print("1. Download workspace archive (complete workspace as zip)")
    if changed_files:
        print(f"2. Download changed files only ({len(changed_files)} files)")
        if len(changed_files) <= 3:
            print("   Changed files:")
            for file_path in changed_files:
                print(f"     {file_path}")
        else:
            print("   First 3 changed files:")
            for file_path in changed_files[:3]:
                print(f"     {file_path}")
            print(f"     ... and {len(changed_files) - 3} more")
    
    while True:
        if changed_files:
            choice = input("Select option (1 or 2): ").strip()
            if choice in ['1', '2']:
                break
        else:
            choice = input("Select option (1): ").strip()
            if choice == '1':
                break
        print("Invalid choice")
    
    try:
        if choice == '1':
            # Download workspace archive
            print("\nDownloading workspace archive...")
            archive_data = api.download_workspace_archive(conv_id)
            
            filename = f"{format_filename(conv_title)}.zip"
            with open(filename, 'wb') as f:
                f.write(archive_data)
            
            print(f"✓ Downloaded workspace archive: {filename}")
            
        else:
            # Download changed files
            zip_path = download_changed_files(api, conv_id, conv_title, changed_files)
            print(f"✓ Downloaded changed files: {Path(zip_path).name}")
    
    except Exception as e:
        print(f"Error during download: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())