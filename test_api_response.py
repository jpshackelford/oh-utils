#!/usr/bin/env python3
"""Test script to inspect what the API actually returns"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path

# Add the conversation_manager to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_api_response():
    """Test what the API actually returns"""
    
    # Use the OH_API_KEY to make a direct API call
    api_key = os.getenv('OH_API_KEY')
    if not api_key:
        print("❌ OH_API_KEY not found")
        return
    
    import requests
    
    # Let's try to get a list of conversations first
    try:
        response = requests.get(
            'https://app.all-hands.dev/api/conversations',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'limit': 1}
        )
        response.raise_for_status()
        conversations = response.json()
        
        if not conversations:
            print("❌ No conversations found")
            return
        
        conv = conversations[0]
        conv_id = conv['conversation_id']
        runtime_id = conv.get('runtime_id')
        session_api_key = conv.get('session_api_key')
        
        print(f"🔍 Testing with conversation: {conv.get('title', 'Untitled')}")
        print(f"📊 Conversation ID: {conv_id}")
        print(f"📊 Runtime ID: {runtime_id}")
        print(f"🔑 Has session key: {bool(session_api_key)}")
        
        if not runtime_id or not session_api_key:
            print("⚠️  No runtime or session key - conversation may not be active")
            return
        
        # Make the workspace download request
        runtime_url = f"https://{runtime_id}.prod-runtime.all-hands.dev"
        url = f"{runtime_url}/api/conversations/{conv_id}/zip-directory"
        
        print(f"\n🔍 Making request to: {url}")
        
        headers = {'X-Session-API-Key': session_api_key}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Content-Type: {response.headers.get('content-type')}")
        print(f"📊 Content-Length: {len(response.content):,} bytes")
        
        # Check if it's a valid ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_path = Path(temp_file.name)
        
        try:
            with zipfile.ZipFile(temp_path, 'r') as zf:
                file_list = zf.namelist()
                print(f"📦 ZIP contains {len(file_list)} entries:")
                
                # Show first few entries
                for i, filename in enumerate(file_list[:10]):
                    info = zf.getinfo(filename)
                    print(f"  {i+1:2d}. {filename} ({info.file_size:,} bytes)")
                
                if len(file_list) > 10:
                    print(f"  ... and {len(file_list) - 10} more files")
                
                # Check if any entries are ZIP files themselves
                zip_entries = [f for f in file_list if f.endswith('.zip')]
                if zip_entries:
                    print(f"\n⚠️  Found {len(zip_entries)} ZIP files inside:")
                    for zip_entry in zip_entries:
                        print(f"    - {zip_entry}")
                        
                        # Extract and inspect the inner ZIP
                        inner_zip_data = zf.read(zip_entry)
                        print(f"      Inner ZIP size: {len(inner_zip_data):,} bytes")
                        
                        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as inner_temp:
                            inner_temp.write(inner_zip_data)
                            inner_path = Path(inner_temp.name)
                        
                        try:
                            with zipfile.ZipFile(inner_path, 'r') as inner_zf:
                                inner_files = inner_zf.namelist()
                                print(f"      Inner ZIP contains {len(inner_files)} files:")
                                for j, inner_file in enumerate(inner_files[:5]):
                                    print(f"        {j+1}. {inner_file}")
                                if len(inner_files) > 5:
                                    print(f"        ... and {len(inner_files) - 5} more")
                        except zipfile.BadZipFile:
                            print(f"      ❌ Inner file {zip_entry} is not a valid ZIP")
                        finally:
                            inner_path.unlink()
                else:
                    print("\n✅ No nested ZIP files found - this is a proper workspace ZIP")
                    
        except zipfile.BadZipFile:
            print("❌ Response is not a valid ZIP file")
            print(f"First 100 bytes: {response.content[:100]}")
        finally:
            temp_path.unlink()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api_response()