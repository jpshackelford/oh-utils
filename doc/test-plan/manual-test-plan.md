# OpenHands Utilities Manual Test Plan

This document provides step-by-step instructions for manually testing all functionality of the OpenHands utilities. It focuses on the `ohc` CLI tool, including its interactive mode (`ohc -i`).

**Note**: The `oh-conversation-manager` tool is legacy and will be removed in future versions. All its functionality has been superseded by `ohc -i` (interactive mode).

## Prerequisites

1. **Environment Setup**:
   ```bash
   cd oh-utils
   uv sync --all-extras --dev
   ```

2. **API Key**: You need a valid OpenHands API key from https://app.all-hands.dev/settings/api-keys
   - Set as environment variable: `export OH_API_KEY=your_api_key_here`
   - Or use the `--api-key` parameter where supported

3. **Live Data Note**: These tests use live production data, so conversation IDs, titles, and counts will vary. The examples show expected output format, not exact content.

4. **Workspace Changes Note**: Commands that show or download workspace changes (`ws-changes`, `ws-download` for changed files) only work with conversations that:
   - Were started with a specific repository (not blank conversations)
   - Have uncommitted and unpushed changes in their workspace
   - Conversations without repositories or changes will show "No uncommitted changes found"

## Test Suite 1: ohc CLI Tool

### 1.1 Basic Help and Version

**Test**: Display main help
```bash
uv run ohc --help
```

**Expected Output**:
```
Usage: ohc [OPTIONS] COMMAND [ARGS]...

  OpenHands Cloud CLI - Manage OpenHands servers and conversations.

Options:
  --version          Show the version and exit.
  -i, --interactive  Run in interactive mode
  --help             Show this message and exit.

Commands:
  conv    Manage OpenHands conversations.
  help    Show help information.
  server  Manage OpenHands server configurations.
```

**Test**: Display version
```bash
uv run ohc --version
```

**Expected Output**: Version number (e.g., `ohc, version 0.1.0`)

### 1.2 Server Management Commands

#### 1.2.1 List Servers (Empty State)

**Test**: List servers when none configured
```bash
uv run ohc server list
```

**Expected Output**:
```
No servers configured.
Use 'ohc server add' to add a server.
```

#### 1.2.2 Add Server Configuration

**Test**: Add server with all parameters
```bash
uv run ohc server add --name production --url https://app.all-hands.dev/api/ --apikey $OH_API_KEY --default
```

**Expected Output**:
```
Testing connection to https://app.all-hands.dev/api/...
✓ Connection successful
✓ Server 'production' added and set as default
```

**Test**: Add server interactively (prompts for missing info)
```bash
uv run ohc server add
```

**Expected Behavior**: 
- Prompts for server name
- Prompts for URL (defaults to https://app.all-hands.dev/api/)
- Prompts for API key (hidden input)
- Prompts whether to set as default
- Tests connection before saving

#### 1.2.3 List Configured Servers

**Test**: List servers after adding one
```bash
uv run ohc server list
```

**Expected Output**:
```
Configured servers:
* production      https://app.all-hands.dev/api/ (default)
```

#### 1.2.4 Test Server Connection

**Test**: Test default server
```bash
uv run ohc server test
```

**Expected Output**:
```
Testing connection to server 'production'...
✓ Connection successful
```

**Test**: Test specific server
```bash
uv run ohc server test production
```

**Expected Output**:
```
Testing connection to server 'production'...
✓ Connection successful
```

#### 1.2.5 Set Default Server

**Test**: Set a server as default
```bash
uv run ohc server set-default production
```

**Expected Output**:
```
✓ Server 'production' set as default
```

#### 1.2.6 Delete Server

**Test**: Delete server with confirmation
```bash
uv run ohc server delete production
```

**Expected Behavior**: Prompts for confirmation, then deletes

**Test**: Delete server without confirmation
```bash
uv run ohc server delete production --force
```

**Expected Output**:
```
✓ Server 'production' deleted
```

### 1.3 Conversation Management Commands

**Prerequisites**: Ensure you have a server configured (repeat section 1.2.2 if needed)

#### 1.3.1 List Conversations

**Test**: List all conversations
```bash
uv run ohc conv list
```

**Expected Output** (format, actual data will vary):
```
Found 20 conversations:
 1. 16b21076 🟢 RUNNING  Create API Reference & Manual Test Plan Docs
 2. ed6ba390 🟢 RUNNING  Integration Tests & Fixture Data Migration Plan
 3. 77471679 🔴 STOPPED  Architectural Review: Interactive vs CLI Commands
 4. 13237430 🔴 STOPPED  Clone & Analyze OpenHands Microagents/Skills Su...
 5. b24872d5 🔴 STOPPED  AWS Device Flow Authentication Setup
...
```

**Test**: List limited number of conversations
```bash
uv run ohc conv list -n 5
```

**Expected Output**: Shows only first 5 conversations

**Test**: List with specific server
```bash
uv run ohc conv list --server production
```

**Expected Output**: Same as default (since production is default)

#### 1.3.2 Show Conversation Details

**Test**: Show details by partial conversation ID
```bash
uv run ohc conv show 16b21076
```

**Expected Output** (format, actual data will vary):
```
Conversation Details:
  ID: 16b2107670154699801ad663801f0534
  Title: Create API Reference & Manual Test Plan Docs
  Status: 🟢 RUNNING
  Runtime Status: STATUS$READY
  Runtime ID: zxkloyqesljibtda
  Created: 2025-11-26T05:27:39.954433Z
  Last Updated: 2025-11-26T05:50:45.734932Z
  URL: https://zxkloyqesljibtda.prod-runtime.all-hands.dev/api/conversations/16b2107670154699801ad663801f0534

Uncommitted Files (1):
    ➕ Added/New (1):
      oh-utils/doc/test-plan/openhands-api-reference.md
```

**Test**: Show details by full conversation ID
```bash
uv run ohc conv show 16b2107670154699801ad663801f0534
```

**Expected Output**: Same as above

**Test**: Show details by conversation number (for convenience)
```bash
uv run ohc conv show 1
```

**Expected Output**: Same as above (matches conversation #1 from list)

#### 1.3.3 Wake Up Conversations

**Test**: Wake conversation by partial ID
```bash
uv run ohc conv wake 77471679
```

**Expected Output** (if conversation is stopped):
```
Waking up conversation: Architectural Review: Interactive vs CLI Commands
✓ Conversation started successfully
URL: https://[runtime-id].prod-runtime.all-hands.dev/api/conversations/77471679...
```

**Test**: Wake conversation by full ID
```bash
uv run ohc conv wake 77471679a1b2c3d4e5f6789012345678901234
```

**Expected Output**: Similar to above

**Test**: Wake conversation by number (for convenience)
```bash
uv run ohc conv wake 3
```

**Expected Output**: Similar to above (wakes conversation #3 from list)

#### 1.3.4 Show Workspace Changes

**Important Note**: This command only shows changes for conversations that:
1. Were started with a specific repository (not blank conversations)
2. Have uncommitted and unpushed changes in their workspace

**Test**: Show git changes for a conversation with repository and changes
```bash
uv run ohc conv ws-changes 16b21076
```

**Expected Output** (format will vary based on actual changes):
```
Workspace Changes for 16b21076:
Title: Create API Reference & Manual Test Plan Docs
Total files changed: 1

➕ Added/New (1):
  oh-utils/doc/test-plan/openhands-api-reference.md
```

**Test**: Show changes for conversation without repository or no changes
```bash
uv run ohc conv ws-changes 77471679
```

**Expected Output**:
```
Workspace Changes for 77471679:
Title: Architectural Review: Interactive vs CLI Commands
No uncommitted changes found.
```

**Test**: Show changes using conversation number (for convenience)
```bash
uv run ohc conv ws-changes 1
```

**Expected Output**: Same as first example above

#### 1.3.5 Download Workspace Archive

**Important Note**: This command downloads the entire workspace. For conversations with repository changes, use this to get all files. For changed files only, this downloads a ZIP containing just the uncommitted changes.

**Test**: Download workspace as ZIP using conversation ID
```bash
uv run ohc conv ws-download 16b21076
```

**Expected Output**:
```
Downloading workspace for conversation 16b21076...
✓ Workspace downloaded: 16b2107670154699801ad663801f0534.zip (X.X MB)
```

**Test**: Download with custom output filename
```bash
uv run ohc conv ws-download 16b21076 -o my-workspace.zip
```

**Expected Output**:
```
Downloading workspace for conversation 16b21076...
✓ Workspace downloaded: my-workspace.zip (X.X MB)
```

**Test**: Download using conversation number (for convenience)
```bash
uv run ohc conv ws-download 1
```

**Expected Output**: Same as first example above

#### 1.3.6 Download Trajectory

**Test**: Download conversation trajectory using conversation ID
```bash
uv run ohc conv trajectory 16b21076
```

**Expected Output**:
```
Downloading trajectory for conversation 16b21076...
✓ Trajectory downloaded: 16b2107670154699801ad663801f0534_trajectory.json (X.X KB)
```

**Test**: Download with custom filename
```bash
uv run ohc conv trajectory 16b21076 -o my-trajectory.json
```

**Expected Output**:
```
Downloading trajectory for conversation 16b21076...
✓ Trajectory downloaded: my-trajectory.json (X.X KB)
```

**Test**: Download using conversation number (for convenience)
```bash
uv run ohc conv trajectory 1
```

**Expected Output**: Same as first example above

### 1.4 Interactive Mode (ohc -i)

**Test**: Start interactive mode
```bash
uv run ohc -i
```

**Expected Behavior**:
1. If no servers configured, prompts to add one
2. If servers configured, starts interactive conversation manager
3. Shows conversation list in table format
4. Provides command prompt

**Interactive Commands to Test**:
- `h` - Show help
- `r` - Refresh conversation list
- `w 16b21076` - Wake conversation by ID
- `w 1` - Wake conversation #1 (by number)
- `s 16b21076` - Show details for conversation by ID
- `s 1` - Show details for conversation #1 (by number)
- `f 16b21076` - Download changed files for conversation by ID
- `f 1` - Download changed files for conversation #1 (by number)
- `t 16b21076` - Download trajectory for conversation by ID
- `t 1` - Download trajectory for conversation #1 (by number)
- `a 16b21076` - Download workspace for conversation by ID
- `a 1` - Download workspace for conversation #1 (by number)
- `n` - Next page (if multiple pages)
- `p` - Previous page
- `q` - Quit

**Note**: Interactive mode may have issues with automated testing due to input handling. Manual testing recommended.

### 1.5 Error Handling Tests

#### 1.5.1 Invalid Server Configuration

**Test**: Try to use commands without server configured
```bash
# First delete any existing servers
uv run ohc server delete production --force
uv run ohc conv list
```

**Expected Output**:
```
✗ No servers configured. Use 'ohc server add' to add a server.
```

#### 1.5.2 Invalid Conversation References

**Test**: Reference non-existent conversation ID
```bash
uv run ohc conv show nonexistent
```

**Expected Output**:
```
✗ No conversation found with ID starting with 'nonexistent'
```

**Test**: Reference non-existent conversation number
```bash
uv run ohc conv show 999
```

**Expected Output**:
```
✗ Conversation number 999 is out of range (1-X)
```

#### 1.5.3 Ambiguous Conversation ID

**Test**: Use partial ID that matches multiple conversations
```bash
uv run ohc conv show a
```

**Expected Output** (if multiple conversations start with 'a'):
```
✗ Multiple conversations match 'a'. Please use a longer ID:
  a7acdf5a - Fix repo.md placement and merge conflicts
  [additional matches...]
```

## Test Suite 2: Integration Tests

### 2.1 File Downloads

**Test**: Verify downloaded files are valid
1. Download workspace: `uv run ohc conv ws-download 16b21076`
2. Verify ZIP file: `unzip -t [filename].zip`
3. **Expected**: ZIP file should be valid and contain workspace files

**Test**: Verify trajectory files are valid JSON
1. Download trajectory: `uv run ohc conv trajectory 16b21076`
2. Verify JSON: `python -m json.tool [filename]_trajectory.json`
3. **Expected**: Valid JSON with trajectory structure

### 2.2 Cross-Tool Consistency

**Test**: Compare CLI and interactive mode
1. Run: `uv run ohc conv list -n 5`
2. Run: `uv run ohc -i` and compare conversation list
3. **Expected**: Both should show same conversations (order may vary)

**Test**: Compare conversation details
1. Get details with CLI: `uv run ohc conv show 16b21076`
2. Get details with interactive mode: `s 16b21076` in `ohc -i`
3. **Expected**: Same conversation ID, title, and status

### 2.3 State Changes

**Test**: Wake conversation and verify status change
1. Find a stopped conversation: `uv run ohc conv list`
2. Wake it: `uv run ohc conv wake [conversation-id]`
3. Check status: `uv run ohc conv show [conversation-id]`
4. **Expected**: Status should change from STOPPED to RUNNING

## Test Results Documentation

When running these tests, document:

1. **Environment**: OS, Python version, uv version
2. **API Key Type**: Full vs limited permissions
3. **Network Conditions**: Any connectivity issues
4. **Failures**: Commands that don't work as expected
5. **Performance**: Response times for API calls
6. **File Sizes**: Size of downloaded archives and trajectories

## Known Limitations

1. **Interactive Mode**: May not work well with automated testing due to input handling
2. **Live Data**: Conversation IDs and content will vary between test runs
3. **Network Dependency**: All tests require internet connectivity
4. **API Rate Limits**: Rapid testing may hit rate limits
5. **File Permissions**: Download operations require write permissions in current directory

## Troubleshooting

### Common Issues

1. **"No servers configured"**: Run `uv run ohc server add` to configure
2. **"Invalid API key"**: Verify key has full permissions from OpenHands settings
3. **"Connection failed"**: Check internet connectivity and API endpoint
4. **"Conversation not found"**: Use `uv run ohc conv list` to see available conversations
5. **"Permission denied"**: Ensure write permissions for file downloads

### Debug Commands

```bash
# Test API connectivity
uv run ohc server test

# Verify server configuration
uv run ohc server list

# Check conversation availability
uv run ohc conv list -n 1

# Test with explicit API key
uv run oh-conversation-manager --api-key $OH_API_KEY --test
```

This manual test plan provides comprehensive coverage of all utility functions and should be executed before any major refactoring to ensure functionality is preserved.