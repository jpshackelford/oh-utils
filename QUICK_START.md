# Quick Start Guide

## Run with uv (No Installation Required)

The simplest way to run the conversation downloader:

```bash
cd /Users/jpshack/oh-utils
uv run oh-conversation-downloader
```

This will:
- ✓ Automatically create a virtual environment
- ✓ Install dependencies (requests)
- ✓ Run the utility

## Install and Run

If you prefer to install it first:

```bash
cd /Users/jpshack/oh-utils
uv pip install -e .
```

Then run with:
```bash
uv run oh-conversation-downloader
```

## Alternative: Run Script Directly

You can also run the Python script directly without uv:

```bash
cd /Users/jpshack/oh-utils
python3 openhands_api_utility/openhands_utility.py
```

## What It Does

1. Uses your stored API key (already configured at `~/.openhands/config.json`)
2. Fetches all your OpenHands conversations
3. Displays them with pagination
4. Lets you select a conversation to download
5. Downloads either:
   - Complete workspace archive (zip)
   - Changed files only (zip)

## Navigation

- **[number]** - Select conversation by number
- **n** - Next page
- **p** - Previous page  
- **q** - Quit

## Example Session

```bash
$ cd /Users/jpshack/oh-utils
$ uv run oh-conversation-downloader

OpenHands API Utility
==================================================
✓ Using stored API key

Fetching conversations...
Found 34 conversations total.

Recent Conversations:
--------------------------------------------------------------------------------
 1. OpenHands API Utility for Conversation Management
    Status: RUNNING | Repository: None
    Last updated: 2025-11-13T12:10:15.533608Z
...

Commands: [number] to select conversation, [q]uit
Enter choice: 1

Selected: OpenHands API Utility for Conversation Management

Options:
1. Download workspace archive (complete workspace as zip)
2. Download changed files only (5 files)

Select option (1 or 2): 2

Downloading 5 changed files...
  [1/5] src/main.py
  [2/5] src/utils.py
  ...
✓ Downloaded changed files: openhands-api-utility-changes.zip
```
