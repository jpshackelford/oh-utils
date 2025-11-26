# OpenHands Utilities Test Execution Checklist Template

**Date:** [DATE]  
**Tester:** [TESTER_NAME]  
**Environment:** [OS/Python/uv versions]  
**API Key Type:** [Full/Limited permissions]  
**Branch:** [BRANCH_NAME]  

## Prerequisites

- [ ] Environment setup completed: `uv sync --all-extras --dev`
- [ ] API key configured: `export OH_API_KEY=your_api_key_here`
- [ ] Working directory: `cd oh-utils`
- [ ] Network connectivity verified

**Notes:**
```
[Environment setup notes]
```

## Test Suite 1: ohc CLI Tool

### 1.1 Basic Help and Version

- [ ] **Test 1.1.1:** Display main help (`uv run ohc --help`)
  - **Expected:** Usage message with commands listed
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.1.2:** Display version (`uv run ohc --version`)
  - **Expected:** Version number displayed
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

### 1.2 Server Management Commands

#### 1.2.1 List Servers (Empty State)

- [ ] **Test 1.2.1:** List servers when none configured (`uv run ohc server list`)
  - **Expected:** "No servers configured" message
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.2.2 Add Server Configuration

- [ ] **Test 1.2.2a:** Add server with all parameters
  - **Command:** `uv run ohc server add --name production --url https://app.all-hands.dev/api/ --apikey $OH_API_KEY --default`
  - **Expected:** Connection test success, server added as default
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.2.2b:** Add server interactively (`uv run ohc server add`)
  - **Expected:** Prompts for name, URL, API key, default setting
  - **Result:** ✅ PASS / ❌ FAIL / ⏭️ SKIP (interactive)
  - **Notes:** 

#### 1.2.3 List Configured Servers

- [ ] **Test 1.2.3:** List servers after adding (`uv run ohc server list`)
  - **Expected:** Shows configured server with default marker
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.2.4 Test Server Connection

- [ ] **Test 1.2.4a:** Test default server (`uv run ohc server test`)
  - **Expected:** Connection successful message
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.2.4b:** Test specific server (`uv run ohc server test production`)
  - **Expected:** Connection successful message
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.2.5 Set Default Server

- [ ] **Test 1.2.5:** Set server as default (`uv run ohc server set-default production`)
  - **Expected:** Default server set confirmation
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.2.6 Delete Server

- [ ] **Test 1.2.6a:** Delete server with confirmation (`uv run ohc server delete production`)
  - **Expected:** Prompts for confirmation, then deletes
  - **Result:** ✅ PASS / ❌ FAIL / ⏭️ SKIP (interactive)
  - **Notes:** 

- [ ] **Test 1.2.6b:** Delete server without confirmation (`uv run ohc server delete production --force`)
  - **Expected:** Server deleted without prompt
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

### 1.3 Conversation Management Commands

**Prerequisites:** Server configured (re-add if deleted in 1.2.6)

#### 1.3.1 List Conversations

- [ ] **Test 1.3.1a:** List all conversations (`uv run ohc conv list`)
  - **Expected:** Numbered list with ID, status, title
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.1b:** List limited conversations (`uv run ohc conv list -n 5`)
  - **Expected:** Shows only first 5 conversations
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.1c:** List with specific server (`uv run ohc conv list --server production`)
  - **Expected:** Same as default server
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.3.2 Show Conversation Details

- [ ] **Test 1.3.2a:** Show by partial ID (`uv run ohc conv show [PARTIAL_ID]`)
  - **Expected:** Full conversation details
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.2b:** Show by full ID (`uv run ohc conv show [FULL_ID]`)
  - **Expected:** Same details as partial ID
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.2c:** Show by conversation number (`uv run ohc conv show 1`)
  - **Expected:** Details for conversation #1 from list
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.3.3 Wake Up Conversations

- [ ] **Test 1.3.3a:** Wake by partial ID (`uv run ohc conv wake [STOPPED_CONV_ID]`)
  - **Expected:** Conversation started successfully or already running
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.3b:** Wake by full ID (`uv run ohc conv wake [FULL_ID]`)
  - **Expected:** Similar to partial ID
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.3c:** Wake by number (`uv run ohc conv wake [NUMBER]`)
  - **Expected:** Wakes conversation by number
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.3.4 Show Workspace Changes

- [ ] **Test 1.3.4a:** Show changes for conversation with repository (`uv run ohc conv ws-changes [CONV_ID]`)
  - **Expected:** Lists uncommitted changes or "No uncommitted changes"
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.4b:** Show changes for conversation without repository (`uv run ohc conv ws-changes [CONV_ID]`)
  - **Expected:** "No uncommitted changes found"
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.4c:** Show changes by number (`uv run ohc conv ws-changes 1`)
  - **Expected:** Changes for conversation #1
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.3.5 Download Workspace Archive

- [ ] **Test 1.3.5a:** Download workspace (`uv run ohc conv ws-download [CONV_ID]`)
  - **Expected:** ZIP file downloaded with conversation ID name
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.5b:** Download with custom filename (`uv run ohc conv ws-download [CONV_ID] -o my-workspace.zip`)
  - **Expected:** ZIP file with custom name
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.5c:** Download by number (`uv run ohc conv ws-download 1`)
  - **Expected:** ZIP file for conversation #1
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.3.6 Download Trajectory

- [ ] **Test 1.3.6a:** Download trajectory (`uv run ohc conv trajectory [CONV_ID]`)
  - **Expected:** JSON file with trajectory data
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.6b:** Download with custom filename (`uv run ohc conv trajectory [CONV_ID] -o my-trajectory.json`)
  - **Expected:** JSON file with custom name
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.3.6c:** Download by number (`uv run ohc conv trajectory 1`)
  - **Expected:** JSON file for conversation #1
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

### 1.4 Interactive Mode

- [ ] **Test 1.4:** Start interactive mode (`uv run ohc -i`)
  - **Expected:** Interactive conversation manager starts
  - **Result:** ✅ PASS / ❌ FAIL / ⏭️ SKIP (interactive)
  - **Notes:** 

**Interactive Commands (if testing):**
- [ ] `h` - Show help
- [ ] `r` - Refresh conversation list
- [ ] `w [ID/NUM]` - Wake conversation
- [ ] `s [ID/NUM]` - Show details
- [ ] `f [ID/NUM]` - Download changed files
- [ ] `t [ID/NUM]` - Download trajectory
- [ ] `a [ID/NUM]` - Download workspace
- [ ] `n` - Next page
- [ ] `p` - Previous page
- [ ] `q` - Quit

### 1.5 Error Handling Tests

#### 1.5.1 Invalid Server Configuration

- [ ] **Test 1.5.1:** Commands without server configured
  - **Setup:** Delete servers first: `uv run ohc server delete production --force`
  - **Command:** `uv run ohc conv list`
  - **Expected:** "No servers configured" error
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.5.2 Invalid Conversation References

- [ ] **Test 1.5.2a:** Non-existent conversation ID (`uv run ohc conv show nonexistent`)
  - **Expected:** "No conversation found" error
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 1.5.2b:** Non-existent conversation number (`uv run ohc conv show 999`)
  - **Expected:** "Conversation number out of range" error
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

#### 1.5.3 Ambiguous Conversation ID

- [ ] **Test 1.5.3:** Partial ID matching multiple conversations (`uv run ohc conv show a`)
  - **Expected:** "Multiple conversations match" error with suggestions
  - **Result:** ✅ PASS / ❌ FAIL / 🔄 N/A (no ambiguous IDs)
  - **Notes:** 

## Test Suite 2: Integration Tests

### 2.1 File Downloads

- [ ] **Test 2.1.1:** Verify downloaded ZIP files
  - **Command:** `unzip -t [filename].zip`
  - **Expected:** Valid ZIP file
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 2.1.2:** Verify trajectory JSON files
  - **Command:** `python -m json.tool [filename]_trajectory.json`
  - **Expected:** Valid JSON structure
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

### 2.2 Cross-Tool Consistency

- [ ] **Test 2.2.1:** Compare CLI and interactive mode
  - **Commands:** `uv run ohc conv list -n 5` vs `uv run ohc -i`
  - **Expected:** Same conversations shown
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

- [ ] **Test 2.2.2:** Compare conversation details
  - **Commands:** `uv run ohc conv show [ID]` vs interactive `s [ID]`
  - **Expected:** Same ID, title, status
  - **Result:** ✅ PASS / ❌ FAIL / ⏭️ SKIP (interactive)
  - **Notes:** 

### 2.3 State Changes

- [ ] **Test 2.3:** Wake conversation and verify status change
  - **Steps:** Find stopped conversation, wake it, check status
  - **Expected:** Status changes from STOPPED to RUNNING
  - **Result:** ✅ PASS / ❌ FAIL
  - **Notes:** 

## Test Results Summary

**Total Tests:** [COUNT]  
**Passed:** [COUNT]  
**Failed:** [COUNT]  
**Skipped:** [COUNT]  

### Environment Information
- **OS:** [OS_INFO]
- **Python Version:** [PYTHON_VERSION]
- **uv Version:** [UV_VERSION]
- **API Key Type:** [FULL/LIMITED]
- **Network Conditions:** [NOTES]

### Performance Notes
- **API Response Times:** [NOTES]
- **File Download Sizes:** [NOTES]
- **Overall Performance:** [NOTES]

### Issues Found

#### Test Plan Accuracy Issues
```
[List any places where the test plan seems wrong or needs clarification]
```

#### Functionality Issues
```
[List any actual bugs or problems found during testing]
```

### Recommendations
```
[Suggestions for test plan improvements or code fixes]
```

## Files Created During Testing
```
[List of downloaded files and their sizes]
```

## Cleanup Commands
```bash
# Remove downloaded test files
rm -f *.zip *.json

# Reset server configuration if needed
uv run ohc server delete production --force
```