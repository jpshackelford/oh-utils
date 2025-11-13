# OpenHands API Utility

A Python utility to interact with the OpenHands Cloud API for managing conversations and downloading workspace files.

## Features

- **API Key Management**: Securely stores and validates your OpenHands API key
- **Conversation Listing**: Browse all your conversations with pagination support
- **Workspace Downloads**: Download complete workspace archives or just changed files
- **User-Friendly Interface**: Interactive command-line interface with clear prompts

## Prerequisites

- Python 3.6 or higher
- `requests` library (usually included with Python)

## Setup

1. Get your OpenHands API key:
   - Go to [https://app.all-hands.dev/settings/api-keys](https://app.all-hands.dev/settings/api-keys)
   - Click "Create API Key"
   - Give it a descriptive name and copy the generated key

2. Make the utility executable:
   ```bash
   chmod +x openhands_utility.py
   ```

## Usage

Run the utility:
```bash
python3 openhands_utility.py
```

### First Run

On first run, the utility will:
1. Prompt you for your OpenHands API key
2. Validate the key by testing the connection
3. Store the key securely in `~/.openhands/config.json` with restricted permissions

### Subsequent Runs

The utility will:
1. Use your stored API key (if valid)
2. Fetch and display your conversations with pagination
3. Allow you to select a conversation by number
4. Offer download options:
   - **Workspace Archive**: Complete workspace as a zip file
   - **Changed Files Only**: Just the files that were modified (if available)

### Navigation Commands

When viewing conversations:
- `[number]`: Select a conversation by its number
- `n`: Next page (if multiple pages)
- `p`: Previous page (if multiple pages)
- `q`: Quit the utility

## File Storage

- **API Key**: Stored in `~/.openhands/config.json` with 600 permissions (user read/write only)
- **Downloads**: Saved to the current working directory
  - Workspace archives: `conversation-title.zip`
  - Changed files: `conversation-title-changes.zip`

## File Naming

Conversation titles are converted to filenames by:
- Converting to lowercase
- Replacing spaces with dashes
- Removing special characters
- Truncating to 30 characters maximum
- Removing consecutive dashes

Example: "Fix Bug in Authentication System" → "fix-bug-in-authentication-system"

## Error Handling

The utility handles common errors gracefully:
- Invalid API keys
- Network connectivity issues
- Missing conversations
- File download failures

## Security

- API keys are stored with restrictive file permissions (600)
- Keys are validated before use
- No sensitive information is logged or displayed

## API Endpoints Used

- `GET /api/options/models` - API key validation
- `GET /api/conversations/search` - List conversations with pagination
- `GET /api/conversations/{id}/git/changes` - Get changed files
- `GET /api/conversations/{id}/zip-directory` - Download workspace archive
- `GET /api/conversations/{id}/select-file` - Download individual files

## Troubleshooting

### "Invalid API key" error
- Verify your API key is correct
- Check that you have access to the OpenHands Cloud service
- Try generating a new API key

### "No conversations found"
- Ensure you have created conversations in OpenHands Cloud
- Check your account permissions

### Download failures
- Verify the conversation exists and is accessible
- Check your internet connection
- Ensure you have write permissions in the current directory

## License

This utility is provided as-is for interacting with the OpenHands Cloud API.