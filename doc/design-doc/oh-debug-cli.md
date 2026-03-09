# OpenHands Debug CLI Tool - Design Document

## Overview

A command-line utility for troubleshooting OpenHands Enterprise deployments, with a focus on diagnosing runtime resource issues, viewing logs, and investigating conversation failures.

### Problem Statement

Users report conversations erroring out with messages indicating resources have run out. Support engineers need a streamlined way to:

1. Investigate specific runtime failures via Kubernetes events and logs
2. Check cluster-wide health and identify resource pressure
3. View app server logs for broader diagnostics
4. Understand and modify runtime resource allocation

### Goals

- **Simple setup**: Auto-detect configuration from existing deployments
- **Multi-environment**: Support production, staging, and other environments
- **Actionable output**: Provide recommendations, not just raw data
- **Scriptable**: Support JSON output and exit codes for automation

---

## Integration with oh-utils

This tool will be implemented as part of the existing `oh-utils` repository, which already provides:
- `ohc` CLI for OpenHands Cloud conversation management
- Established patterns for configuration, commands, and display formatting
- Testing infrastructure with >78% coverage

### Integration Options

**Option A: Subcommand of `ohc`** (Recommended)
```bash
ohc debug runtime <ID>
ohc debug health
ohc debug configure
```

**Option B: Separate Entry Point**
```bash
oh-debug runtime <ID>
```

Option A is recommended to leverage existing infrastructure and provide a unified CLI experience.

---

## Configuration

### File Location

Following the XDG Base Directory Specification (consistent with existing `ohc` configuration):

```
~/.config/ohc/debug.json
```

Or with `$XDG_CONFIG_HOME` set:
```
$XDG_CONFIG_HOME/ohc/debug.json
```

### Configuration Schema

Using JSON format for consistency with the existing `ohc` configuration:

```json
{
  "environments": {
    "production": {
      "app": {
        "kube_context": "gke_myproject_us-central1_prod",
        "namespace": "openhands"
      },
      "runtime": {
        "kube_context": "gke_myproject_us-central1_prod",
        "namespace": "runtime-pods"
      }
    },
    "staging": {
      "app": {
        "kube_context": "gke_myproject_us-central1_staging",
        "namespace": "openhands"
      },
      "runtime": {
        "namespace": "runtime-pods"
      }
    },
    "prod-isolated": {
      "app": {
        "kube_context": "gke_myproject_us-central1_app",
        "namespace": "openhands"
      },
      "runtime": {
        "kube_context": "gke_myproject_us-west1_runtimes",
        "namespace": "runtime-pods"
      }
    }
  },
  "default_environment": "production"
}
```

### Configuration Resolution

When runtime settings are not fully specified:

| If runtime.kube_context is... | Then use... |
|-------------------------------|-------------|
| Specified | The specified value |
| Omitted | `app.kube_context` |

| If runtime.namespace is... | Then use... |
|----------------------------|-------------|
| Specified | The specified value |
| Omitted | `runtime-pods` (default) |

---

## Interactive Setup Flow

### Command

```bash
ohc debug configure        # If integrated as subcommand (recommended)
oh-debug configure         # If standalone entry point
```

### Flow

```
OpenHands Debug Tool - Configuration Setup
==========================================

? Environment name: production

App Cluster (where OpenHands Enterprise Server runs)
----------------------------------------------------
Available kubectl contexts:
  1. gke_myproject_us-central1_prod
  2. gke_myproject_us-central1_staging  
  3. minikube

? Select app cluster context [1-3]: 1

? App namespace: openhands

Detecting runtime configuration...
✓ Found runtime-api deployment
✓ Detected: Runtimes in same cluster, namespace 'runtime-pods'

Runtime Cluster (where runtime pods run)
----------------------------------------
  Context:   gke_myproject_us-central1_prod (same as app)
  Namespace: runtime-pods

? Use detected settings? [Y/n]: y

✓ Configuration saved to ~/.config/ohc/debug.json

Set as default environment? [Y/n]: y
✓ 'production' set as default

Quick test:
  ohc debug health
```

### Auto-Detection Logic

After obtaining app cluster context and namespace, the tool:

1. Connects to the app cluster using the specified context
2. Finds the runtime-api deployment in the app namespace
3. Reads environment variables from the deployment:

| Env Var | What it tells us |
|---------|------------------|
| `RUNTIME_IN_SAME_CLUSTER` | Whether runtimes run in same cluster (`true`/`false`) |
| `K8S_NAMESPACE` | Runtime pods namespace (default: `runtime-pods`) |
| `GKE_CLUSTER_NAME` | Target GKE cluster name (if different cluster) |
| `GCP_PROJECT` | GCP project ID |
| `GCP_REGION` | GCP region |
| `AWS_REGION` | AWS region (for EKS) |
| `CLUSTER_NAME` | EKS cluster name |

4. Constructs the runtime cluster context:
   - If `RUNTIME_IN_SAME_CLUSTER=true`: Use app context
   - If GKE: Construct `gke_{project}_{region}_{cluster}` 
   - If EKS: Match against available contexts

5. Presents detected settings for user confirmation

### Different Cluster Flow

If auto-detection finds runtimes in a different cluster:

```
Detecting runtime configuration...
✓ Found runtime-api deployment
✓ Detected: Runtimes in DIFFERENT cluster
  - Project: myproject
  - Region: us-west1  
  - Cluster: runtimes-cluster
  - Namespace: runtime-pods

Runtime Cluster (where runtime pods run)
----------------------------------------
Looking for matching kubectl context...
✓ Found: gke_myproject_us-west1_runtimes-cluster

  Context:   gke_myproject_us-west1_runtimes-cluster
  Namespace: runtime-pods

? Use detected settings? [Y/n]: y
```

If no matching context found:

```
⚠ No matching kubectl context found for cluster 'runtimes-cluster'

Available contexts:
  1. gke_myproject_us-central1_prod
  2. gke_myproject_us-central1_staging

? Select runtime cluster context, or 'q' to quit and configure kubectl: 
```

---

## CLI Commands

> **Note**: Commands shown below use `ohc debug` (recommended integration). If implemented as standalone, replace with `oh-debug`.

### Configuration Commands

```bash
ohc debug configure                      # Interactive setup for new environment
ohc debug configure --add <name>         # Add another environment
ohc debug configure --list               # List configured environments
ohc debug configure --default <name>     # Set default environment
ohc debug configure --show               # Show current configuration
ohc debug configure --show <name>        # Show specific environment config
ohc debug configure --remove <name>      # Remove an environment
ohc debug configure --test               # Test connectivity to configured clusters
```

### Runtime Investigation Commands

```bash
# Investigate a specific runtime
ohc debug runtime <RUNTIME_ID or SESSION_ID>

# With options
ohc debug runtime <ID> --events          # Full event history
ohc debug runtime <ID> --logs            # Container logs
ohc debug runtime <ID> --logs --previous # Logs from crashed container
ohc debug runtime <ID> --describe        # Full pod description
ohc debug runtime <ID> --yaml            # Pod YAML
ohc debug runtime <ID> --all             # Everything
```

### Health & Discovery Commands

```bash
# Cluster health overview
ohc debug health

# List runtimes with issues
ohc debug list --errors                  # Error state runtimes
ohc debug list --restarts                # Runtimes with restarts
ohc debug list --restarts --min 3        # At least 3 restarts
ohc debug list --oom                     # OOMKilled runtimes
ohc debug list --recent                  # Recently created (last 1h)
```

### App Server Commands

```bash
# App server logs
ohc debug app logs                       # App server logs
ohc debug app logs --follow              # Stream logs
ohc debug app logs --since 1h            # Logs from last hour
ohc debug app logs --component api       # Specific component

# App server health
ohc debug app status                     # Deployment status
ohc debug app pods                       # List app pods
```

### Watch Mode

```bash
ohc debug watch                          # Stream all runtime events
ohc debug watch --errors                 # Only error events
ohc debug watch <RUNTIME_ID>             # Watch specific runtime
```

### Global Options

```bash
ohc debug --env <name> <command>         # Use specific environment
ohc debug -e staging <command>           # Short form
ohc debug --output json <command>        # JSON output
ohc debug --output table <command>       # Table output (default for lists)
ohc debug --quiet <command>              # Minimal output (IDs only)
ohc debug --verbose <command>            # Debug output
```

---

## Output Examples

### Runtime Investigation

```
$ ohc debug runtime abc123xyz

Runtime: abc123xyz
Session: sess-456789
Status:  ERROR (CrashLoopBackOff)
Created: 2024-01-15 10:23:45 UTC (2 hours ago)
Image:   ghcr.io/all-hands-ai/runtime:0.15.0

Resources:
  CPU:    1000m requested / 1000m limit
  Memory: 2048Mi requested / 2048Mi limit (100% used) ⚠️
  
Pod Status:
  Restarts: 3
  Last Restart: 5 minutes ago
  Restart Reason: OOMKilled

Recent Events:
  5m ago   Warning   OOMKilled        Container exceeded memory limit
  5m ago   Normal    Pulled           Successfully pulled image
  8m ago   Warning   OOMKilled        Container exceeded memory limit
  12m ago  Warning   OOMKilled        Container exceeded memory limit
  15m ago  Normal    Started          Started container runtime

💡 Recommendation: This runtime is repeatedly hitting memory limits.
   Consider increasing resource_factor for this user's organization.
   
   Current org setting: resource_factor=1 (2048Mi memory)
   Suggested: resource_factor=2 (4096Mi memory)
   
   To update via API:
   curl -X PATCH "https://app.all-hands.dev/api/organizations/{ORG_ID}" \
     -H "Authorization: Bearer {TOKEN}" \
     -d '{"remote_runtime_resource_factor": 2}'
```

### Health Overview

```
$ ohc debug health

OpenHands Environment: production
=================================

App Cluster: gke_myproject_us-central1_prod
  Namespace: openhands
  Status:    ✓ Healthy
  Pods:      3/3 running

Runtime Cluster: gke_myproject_us-central1_prod
  Namespace: runtime-pods
  Status:    ⚠ Issues detected
  
Runtime Summary (last 24h):
  Total:      142
  Running:    128 (90%)
  Starting:     8 (6%)
  Error:        6 (4%) ⚠

Resource Issues (last 24h):
  OOMKilled:          4 runtimes
  Evicted:            0 runtimes
  FailedScheduling:   2 runtimes

Top Issues:
  runtime-abc123    5 restarts (OOMKilled) - user: acme-corp
  runtime-def456    3 restarts (OOMKilled) - user: example-org
  runtime-ghi789    2 restarts (OOMKilled) - user: acme-corp

⚠ Recommendation: 3 runtimes from 'acme-corp' have OOM issues.
  Consider increasing their org's resource_factor.
```

### List with Filters

```
$ ohc debug list --oom --since 24h

RUNTIME ID      SESSION         STATUS    RESTARTS  REASON      AGE    ORG
abc123xyz       sess-456789     Error     5         OOMKilled   2h     acme-corp
def456abc       sess-123456     Error     3         OOMKilled   5h     example-org
ghi789def       sess-789012     Running   2         OOMKilled   12h    acme-corp

3 runtimes with OOM issues in the last 24 hours
```

### JSON Output

```
$ ohc debug runtime abc123xyz --output json

{
  "runtime_id": "abc123xyz",
  "session_id": "sess-456789",
  "status": "error",
  "pod_status": "crash_loop_backoff",
  "restarts": 3,
  "restart_reasons": ["OOMKilled", "OOMKilled", "OOMKilled"],
  "resources": {
    "cpu_request": "1000m",
    "cpu_limit": "1000m", 
    "memory_request": "2048Mi",
    "memory_limit": "2048Mi"
  },
  "events": [...],
  "recommendation": {
    "issue": "memory_limit_exceeded",
    "suggestion": "increase_resource_factor",
    "current_factor": 1,
    "suggested_factor": 2
  }
}
```

---

## Implementation Considerations

### Technology Stack

Building on the existing oh-utils codebase:

- **Language**: Python 3.8+ (per existing `pyproject.toml`, compatible with 3.11+)
- **CLI Framework**: `click>=8.0.0` (already used by ohc)
- **Kubernetes Client**: `kubernetes` Python client (new dependency)
- **Config Parsing**: `json` (built-in, consistent with existing ohc config)
- **Output Formatting**: Terminal-aware formatting (see existing `conversation_display.py` patterns)
- **HTTP Client**: `requests>=2.25.0` (already used by ohc)

### Reusable Components from ohc

The following existing patterns should be leveraged:

1. **ConfigManager** (`ohc/config.py`): Extend for debug config or create `DebugConfigManager`
2. **Command decorators** (`ohc/command_utils.py`): Pattern for `@with_env_config`
3. **Display formatting** (`ohc/conversation_display.py`): Status icons, dataclasses
4. **Testing infrastructure** (`tests/`): VCR-based fixtures, conftest patterns

### Package Structure

Integrated into existing oh-utils structure:

```
oh-utils/                           # Existing repository
├── pyproject.toml                  # Add kubernetes dependency
├── ohc/
│   ├── __init__.py
│   ├── cli.py                      # Add debug command group
│   ├── config.py                   # Existing config (servers)
│   ├── debug_config.py             # NEW: Debug environment config
│   ├── debug_commands.py           # NEW: Debug command group
│   ├── k8s/                        # NEW: Kubernetes utilities
│   │   ├── __init__.py
│   │   ├── client.py               # K8s client wrapper
│   │   ├── detection.py            # Auto-detection logic
│   │   └── queries.py              # Pod/event queries
│   └── debug/                      # NEW: Debug subcommands
│       ├── __init__.py
│       ├── configure.py
│       ├── runtime.py
│       ├── health.py
│       ├── list_cmd.py             # 'list' is reserved
│       ├── app.py
│       └── watch.py
└── tests/
    ├── test_debug_config.py        # NEW
    ├── test_debug_commands.py      # NEW
    └── fixtures/
        └── k8s/                    # NEW: K8s mock responses
```

### Distribution

The debug functionality is distributed as part of the existing `oh-utils` package:

```bash
# Install oh-utils (includes debug commands)
pip install oh-utils
# or
uv pip install oh-utils

# Run debug commands
ohc debug health
ohc debug runtime <ID>
```

Optionally, a standalone entry point can be added to `pyproject.toml`:

```toml
[project.scripts]
ohc = "ohc.cli:main"
oh-debug = "ohc.debug_commands:main"  # Optional standalone
```

---

## Future Enhancements (Out of Scope for V1)

- [ ] Direct database queries for runtime history
- [ ] Runtime API integration for live status
- [ ] Integration with Datadog/monitoring systems
- [ ] Slack notifications for critical issues
- [ ] Interactive TUI mode
- [ ] Automatic remediation (restart pods, scale resources)

---

## Open Questions

1. ~~**Naming**: `oh-debug`, `openhands-debug`, `ohd`, or something else?~~
   **Resolved**: Recommend `ohc debug` as subcommand for consistency with existing CLI
2. **Should we support `--kubeconfig` override** for non-standard kubeconfig locations?
3. **Caching**: Should we cache cluster info to speed up repeated queries?
4. **Authentication**: Any special handling needed for GKE/EKS auth token refresh?

---

## References

- [oh-utils repository](https://github.com/jpshackelford/oh-utils) - This project
- [runtime-api repository](https://github.com/OpenHands/runtime-api) - Runtime pod management
- [OpenHands repository](https://github.com/OpenHands/OpenHands) - Main application
- [OpenHands-Cloud repository](https://github.com/All-Hands-AI/OpenHands-Cloud) - Helm charts and deployment
