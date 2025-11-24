#!/usr/bin/env python3
"""Debug script to inspect workspace ZIP download"""

import os
import sys
import zipfile
import tempfile
from pathlib import Path

# Add the conversation_manager to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from conversation_manager.conversation_manager import ConversationManager

def debug_workspace_download():
    """Debug the workspace download to see what's happening"""
    
    # Initialize manager
    manager = ConversationManager()
    
    # Load conversations
    print("🔍 Loading conversations...")
    manager.load_conversations()
    
    if not manager.conversations:
        print("❌ No conversations found")
        return
    
    # Use the first conversation for testing
    conv = manager.conversations[0]
    print(f"🔍 Testing with conversation: {conv.formatted_title(60)}")
    
    try:
        # Get fresh conversation data
        fresh_conv_data = manager.api.get_conversation(conv.id)
        from conversation_manager.conversation_manager import Conversation
        fresh_conv = Conversation.from_api_response(fresh_conv_data)
        
        print(f"📊 Runtime ID: {fresh_conv.runtime_id}")
        print(f"🔑 Has session key: {bool(fresh_conv.session_api_key)}")
        
        # Download workspace data
        print("\n🔍 Downloading workspace data...")
        workspace_data = manager.api.download_workspace_archive(
            fresh_conv.id, 
            fresh_conv.runtime_id, 
            fresh_conv.session_api_key
        )
        
        print(f"📊 Downloaded {len(workspace_data):,} bytes")
        
        # Check if it's a valid ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_file.write(workspace_data)
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
                    print("\n✅ No nested ZIP files found")
                    
        except zipfile.BadZipFile:
            print("❌ Downloaded data is not a valid ZIP file")
            print(f"First 100 bytes: {workspace_data[:100]}")
        finally:
            temp_path.unlink()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_workspace_download()