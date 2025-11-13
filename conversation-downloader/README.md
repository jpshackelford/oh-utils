# OpenHands Conversation Downloader

A Python utility to download conversations and their workspace files from the OpenHands Cloud API.

## Features

- 🔐 Secure API token storage in `~/.config/openhands/api_token`
- 📋 List all conversations with pagination (up to 200)
- 🔍 Interactive conversation selection
- 📦 Two download modes:
  - Full workspace archive (all files + metadata)
  - Changed files only (with `-changes` suffix)
- 🗂️ Recursive file scanning from `/workspace/project`
- ⚡ Progress indicators for each file
- 🏷️ Smart archive naming (max 30 chars, lowercase, dashes)
- 🛡️ Rate limit handling & error recovery
- ⚠️ Warns about inactive conversations

## Installation

```bash
# Clone the repository
git clone https://github.com/jpshackelford/oh-utils.git
cd oh-utils/conversation-downloader

# Install dependencies
pip install -r requirements.txt

# Make executable
chmod +x openhands_conversation_downloader.py
```

## Usage

```bash
# Run the utility
./openhands_conversation_downloader.py

# On first run, you'll be prompted for your API token
# Get your token from: https://app.all-hands.dev/settings/api-keys
```

### Workflow

1. **First run**: Prompts for API token, validates, and saves it
2. **Lists conversations**: Shows all available conversations with pagination
3. **Select conversation**: Choose by number (1-N)
4. **Choose download type**:
   - Option 1: Full workspace (all files + metadata)
   - Option 2: Changed files only
5. **Downloads**: Creates ZIP file in current directory
   - Format: `conversation-title.zip` or `conversation-title-changes.zip`
   - Shows progress for each file
   - Reports final file size

## Example Output

```
============================================================
OpenHands Conversation Downloader (Cloud API)
============================================================
Using existing API token.

Fetching conversations...

Found 200 conversation(s):

1. OpenHands API Utility for Conversation Management
   ID: b522951548514d4d973e21b5caf5a40c | Status: RUNNING
   Created: 2025-11-13T11:41:31.169785Z
   Updated: 2025-11-13T12:02:42.885932Z

[... more conversations ...]

Select a conversation (1-200): 1

Selected: OpenHands API Utility for Conversation Management
Status: RUNNING

What would you like to download?
1. Workspace archive (full workspace as ZIP)
2. Files archive with '-changes' suffix

Enter your choice (1 or 2): 2

Collecting files from workspace...
Found 23 file(s)

First few files:
  1. src/main.py
  2. src/utils.py
  3. tests/test_main.py
  ... and 20 more

Downloading files...
  [1/23] src/main.py
  [2/23] src/utils.py
  [... progress for each file ...]

Creating archive: openhands-api-utility-for-conv-changes.zip
✓ Archive created: /current/dir/openhands-api-utility-for-conv-changes.zip (21,908 bytes)
```

## API Details

### Authentication
- **Method**: `X-Session-API-Key` header
- **Token Source**: https://app.all-hands.dev/settings/api-keys

### Endpoints Used
- `GET /api/conversations` - List conversations with pagination
- `GET /api/conversations/{id}` - Get conversation metadata
- `GET {runtime_url}/list-files` - List workspace files
- `GET {runtime_url}/select-file` - Download file content

### Two-Phase Architecture

**Phase 1: List & Select**
```
GET https://app.all-hands.dev/api/conversations
→ Returns: List of conversations with metadata
```

**Phase 2: Access Runtime & Download**
```
1. GET /api/conversations/{id}
   → Extract: runtime_url, session_api_key

2. GET {runtime_url}/list-files?path=/workspace/project
   → Get list of all files recursively

3. For each file:
   GET {runtime_url}/select-file?file={path}
   → Download file content

4. Create ZIP archive with all files
```

## Configuration

### Environment Variables

- `OPENHANDS_USER_ID` (optional): Filter conversations by user ID

### Token Storage

API token is stored at: `~/.config/openhands/api_token` with 600 permissions

## Requirements

- Python 3.7+
- requests >= 2.31.0

## Troubleshooting

### Token Issues
- Ensure token is from: https://app.all-hands.dev/settings/api-keys
- Token is stored in `~/.config/openhands/api_token`
- Delete token file to re-enter: `rm ~/.config/openhands/api_token`

### Rate Limits
- Utility automatically handles rate limits with 0.5s delays between pages
- Fetches max 200 conversations (10 pages × 20 per page)

### File Download Issues
- Check conversation status is RUNNING or STOPPED
- Inactive conversations may not have accessible files
- Network errors are automatically retried

### Empty Workspace
- Some conversations may have no files in `/workspace/project`
- This is normal for conversations without code work

## Testing

Fully tested with:
- ✅ 200 conversations listed
- ✅ 23 files downloaded
- ✅ ZIP archive creation verified
- ✅ End-to-end workflow tested

See `CLOUD_API_SUCCESS.md` for detailed test results.

## Use Cases

- Download workspace before conversation expires
- Archive project files for reference
- Extract code from completed conversations
- Backup important work
- Share conversation workspaces with team

## License

MIT

## Author

Created for OpenHands users who need to download and archive their conversation workspaces.

## Related Tools

This repository may contain other OpenHands utilities. Check the parent directory for additional tools.
