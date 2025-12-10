# Tail Follow Mode Feature

## Overview

The `ohc conv tail` command now supports follow mode with the `-f/--follow` flag, similar to the Unix `tail -f` command for log files. This allows you to monitor a conversation in real-time as new messages and thoughts appear.

## Usage

### Basic tail (show last N messages)

```bash
# Show last message/thought
ohc conv tail <conversation-id>

# Show last 5 messages/thoughts
ohc conv tail <conversation-id> -n 5
```

### Follow mode (continuous monitoring)

```bash
# Follow a conversation (displays new messages as they arrive)
ohc conv tail <conversation-id> -f

# Follow with custom polling interval (default is 2 seconds)
ohc conv tail <conversation-id> -f --interval 1.0
```

## Examples

```bash
# Monitor an active conversation
$ ohc conv tail d1849c3d -f
Following: OpenHands Package Catalog with Skill Registry
Conversation: d1849c3d...
================================================================================
(Press Ctrl+C to stop)

Starting to analyze the codebase...
...
Found the configuration files...
...
Implementing the requested feature...
...
^C
✓ Stopped following conversation
```

## Features

- **Real-time monitoring**: Continuously polls the conversation trajectory and displays new agent messages/thoughts as they appear
- **Partial conversation IDs**: Supports shortened conversation IDs (e.g., `d1849c3d` instead of full ID)
- **Configurable polling**: Adjust the polling interval with `--interval` (default: 2.0 seconds)
- **Clean output**: Shows only message/thought content, separated by `...`
- **Graceful exit**: Press Ctrl+C to stop following

## Implementation Details

- Tracks already-seen event IDs to avoid displaying duplicates
- Continues polling until interrupted with Ctrl+C
- Handles KeyboardInterrupt gracefully
- Uses the same trajectory API as regular tail mode

## Use Cases

- **Development monitoring**: Watch an OpenHands agent work on a task in real-time
- **Debugging**: See agent thoughts as they happen
- **Progress tracking**: Monitor long-running conversations without manual refresh
- **Multi-tasking**: Keep a terminal window open showing agent activity while working on other things
