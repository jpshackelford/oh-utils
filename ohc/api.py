"""
OpenHands API client for the ohc CLI.

Refactored from the original conversation_manager module to support multiple server configurations.
"""

import requests
from urllib.parse import urljoin
from typing import Dict, List, Optional, Any


class OpenHandsAPI:
    """OpenHands API client for conversation management."""
    
    def __init__(self, api_key: str, base_url: str = "https://app.all-hands.dev/api/"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/') + '/'
        self.session = requests.Session()
        self.session.headers.update({
            'X-Session-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test if the API key and URL are valid."""
        try:
            response = self.session.get(urljoin(self.base_url, "options/models"))
            return response.status_code == 200
        except Exception:
            return False
    
    def search_conversations(self, page_id: Optional[str] = None, limit: int = 20) -> Dict:
        """Search conversations with pagination."""
        url = urljoin(self.base_url, "conversations")
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
                    "Please ensure you're using a full API key from your OpenHands settings."
                )
            raise
    
    def get_conversation(self, conversation_id: str) -> Dict:
        """Get detailed information about a specific conversation."""
        url = urljoin(self.base_url, f"conversations/{conversation_id}")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def start_conversation(self, conversation_id: str, providers_set: Optional[List[str]] = None) -> Dict:
        """Start/wake up a conversation."""
        url = urljoin(self.base_url, f"conversations/{conversation_id}/start")
        
        # Prepare the request body with providers_set
        data = {
            "providers_set": providers_set or ["github"]
        }
        
        try:
            response = self.session.post(url, json=data)
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_detail)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"API call failed - {str(e)}")
    
    def get_conversation_changes(self, conversation_id: str, runtime_id: str = None, session_api_key: str = None) -> List[Dict[str, str]]:
        """Get git changes (uncommitted files) for a conversation."""
        if runtime_id:
            # Use runtime URL for active conversations
            runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
            url = urljoin(runtime_url, f"api/conversations/{conversation_id}/git/changes")
            
            # Use session API key for runtime requests
            headers = {}
            if session_api_key:
                headers['X-Session-API-Key'] = session_api_key
            else:
                # Fallback to regular authorization
                headers['Authorization'] = f'Bearer {self.api_key}'
        else:
            # Fallback to main app URL (though this likely won't work for git changes)
            url = urljoin(self.base_url, f"conversations/{conversation_id}/git/changes")
            headers = {}
        
        try:
            response = self.session.get(url, headers=headers)
            if response.status_code == 404:
                # Not a git repository or no changes
                return []
            elif response.status_code == 500:
                # Server error - likely git repository issue
                raise Exception("Git repository not available or corrupted")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []  # No git repository or no changes
            elif e.response.status_code == 500:
                raise Exception("Git repository not available or corrupted")
            raise Exception(f"Failed to get changes: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"API call failed - {str(e)}")
    
    def get_file_content(self, conversation_id: str, file_path: str, runtime_id: str = None, session_api_key: str = None) -> str:
        """Get the content of a specific file from the conversation workspace."""
        if runtime_id:
            # Use runtime URL for active conversations
            runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
            url = urljoin(runtime_url, f"api/conversations/{conversation_id}/select-file")
            
            # Use session API key for runtime requests
            headers = {}
            if session_api_key:
                headers['X-Session-API-Key'] = session_api_key
            else:
                # Fallback to regular authorization
                headers['Authorization'] = f'Bearer {self.api_key}'
        else:
            # Fallback to main app URL
            url = urljoin(self.base_url, f"conversations/{conversation_id}/select-file")
            headers = {}
        
        params = {'file': file_path}
        
        try:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            # API returns JSON with 'code' key containing file content
            result = response.json()
            if isinstance(result, dict) and 'code' in result:
                return result['code']
            else:
                # Fallback if response format is different
                return str(result)
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"File not found: {file_path}")
            elif e.response.status_code == 401:
                raise Exception("Authentication failed - invalid session API key")
            elif e.response.status_code == 500:
                raise Exception("Server error - file may be inaccessible")
            raise Exception(f"Failed to get file content: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"API call failed - {str(e)}")
    
    def download_workspace_archive(self, conversation_id: str, runtime_id: str = None, session_api_key: str = None) -> bytes:
        """Download the workspace archive as a ZIP file."""
        if runtime_id:
            # Use runtime URL for active conversations
            runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
            url = urljoin(runtime_url, f"api/conversations/{conversation_id}/zip-directory")
            
            # Use session API key for runtime requests
            headers = {}
            if session_api_key:
                headers['X-Session-API-Key'] = session_api_key
            else:
                # Fallback to regular authorization
                headers['Authorization'] = f'Bearer {self.api_key}'
        else:
            # Fallback to main app URL
            url = urljoin(self.base_url, f"conversations/{conversation_id}/zip-directory")
            headers = {}
        
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"Workspace not found for conversation {conversation_id}")
            elif e.response.status_code == 401:
                raise Exception("Authentication failed - invalid session API key")
            elif e.response.status_code == 500:
                raise Exception("Server error - workspace may be inaccessible")
            raise Exception(f"Failed to download workspace: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"API call failed - {str(e)}")

    def get_trajectory(self, conversation_id: str, runtime_id: str, session_api_key: str) -> Dict:
        """Get trajectory data for a conversation."""
        if runtime_id:
            # Use runtime URL for active conversations
            runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
            url = urljoin(runtime_url, f"api/conversations/{conversation_id}/trajectory")
            
            # Use session API key for runtime requests
            headers = {}
            if session_api_key:
                headers['X-Session-API-Key'] = session_api_key
            else:
                # Fallback to regular authorization
                headers['Authorization'] = f'Bearer {self.api_key}'
        else:
            # Fallback to main app URL
            url = urljoin(self.base_url, f"conversations/{conversation_id}/trajectory")
            headers = {}
        
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"Trajectory not found for conversation {conversation_id}")
            elif e.response.status_code == 401:
                raise Exception("Authentication failed - invalid session API key")
            elif e.response.status_code == 500:
                raise Exception("Server error - trajectory may be inaccessible")
            raise Exception(f"Failed to get trajectory: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"API call failed - {str(e)}")