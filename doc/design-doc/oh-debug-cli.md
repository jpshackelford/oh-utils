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

## Configuration

### File Location

```
~/.oh-debug/config.yaml
```

### Configuration Schema

```yaml
# ~/.oh-debug/config.yaml

environments:
  production:
    # App cluster - where OpenHands Enterprise Server runs (primary)
    app:
      kube_context: gke_myproject_us-central1_prod
      namespace: openhands
    
    # Runtime cluster - where runtime pods run
    # If omitted, defaults to app cluster values
    runtime:
      kube_context: gke_myproject_us-central1_prod   # optional, defaults to app.kube_context
      namespace: runtime-pods

  staging:
    app:
      kube_context: gke_myproject_us-central1_staging
      namespace: openhands
    runtime:
      namespace: runtime-pods   # context defaults to app context

  # Example: separate clusters for app and runtime
  prod-isolated:
    app:
      kube_context: gke_myproject_us-central1_app
      namespace: openhands
    runtime:
      kube_context: gke_myproject_us-west1_runtimes
      namespace: runtime-pods

# Default environment when --env not specified
default: production
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
oh-debug configure
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

✓ Configuration saved to ~/.oh-debug/config.yaml

Set as default environment? [Y/n]: y
✓ 'production' set as default

Quick test:
  oh-debug health
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

### Configuration Commands

```bash
oh-debug configure                      # Interactive setup for new environment
oh-debug configure --add <name>         # Add another environment
oh-debug configure --list               # List configured environments
oh-debug configure --default <name>     # Set default environment
oh-debug configure --show               # Show current configuration
oh-debug configure --show <name>        # Show specific environment config
oh-debug configure --remove <name>      # Remove an environment
oh-debug configure --test               # Test connectivity to configured clusters
```

### Runtime Investigation Commands

```bash
# Investigate a specific runtime
oh-debug runtime <RUNTIME_ID or SESSION_ID>

# With options
oh-debug runtime <ID> --events          # Full event history
oh-debug runtime <ID> --logs            # Container logs
oh-debug runtime <ID> --logs --previous # Logs from crashed container
oh-debug runtime <ID> --describe        # Full pod description
oh-debug runtime <ID> --yaml            # Pod YAML
oh-debug runtime <ID> --all             # Everything
```

### Health & Discovery Commands

```bash
# Cluster health overview
oh-debug health

# List runtimes with issues
oh-debug list --errors                  # Error state runtimes
oh-debug list --restarts                # Runtimes with restarts
oh-debug list --restarts --min 3        # At least 3 restarts
oh-debug list --oom                     # OOMKilled runtimes
oh-debug list --recent                  # Recently created (last 1h)
```

### App Server Commands

```bash
# App server logs
oh-debug app logs                       # App server logs
oh-debug app logs --follow              # Stream logs
oh-debug app logs --since 1h            # Logs from last hour
oh-debug app logs --component api       # Specific component

# App server health
oh-debug app status                     # Deployment status
oh-debug app pods                       # List app pods
```

### Watch Mode

```bash
oh-debug watch                          # Stream all runtime events
oh-debug watch --errors                 # Only error events
oh-debug watch <RUNTIME_ID>             # Watch specific runtime
```

### Global Options

```bash
oh-debug --env <name> <command>         # Use specific environment
oh-debug -e staging <command>           # Short form
oh-debug --output json <command>        # JSON output
oh-debug --output table <command>       # Table output (default for lists)
oh-debug --quiet <command>              # Minimal output (IDs only)
oh-debug --verbose <command>            # Debug output
```

---

## Output Examples

### Runtime Investigation

```
$ oh-debug runtime abc123xyz

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
$ oh-debug health

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
$ oh-debug list --oom --since 24h

RUNTIME ID      SESSION         STATUS    RESTARTS  REASON      AGE    ORG
abc123xyz       sess-456789     Error     5         OOMKilled   2h     acme-corp
def456abc       sess-123456     Error     3         OOMKilled   5h     example-org
ghi789def       sess-789012     Running   2         OOMKilled   12h    acme-corp

3 runtimes with OOM issues in the last 24 hours
```

### JSON Output

```
$ oh-debug runtime abc123xyz --output json

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

- **Language**: Python 3.11+ (consistent with OpenHands ecosystem)
- **CLI Framework**: `click` or `typer` (for argument parsing, help generation)
- **Kubernetes Client**: `kubernetes` Python client
- **Config Parsing**: `pyyaml`
- **Output Formatting**: `rich` (for tables, colors, progress)
- **HTTP Client**: `httpx` (if API calls needed later)

### Package Structure

```
oh-debug/
├── pyproject.toml
├── README.md
├── src/
│   └── oh_debug/
│       ├── __init__.py
│       ├── cli.py              # Main CLI entry point
│       ├── config/
│       │   ├── __init__.py
│       │   ├── manager.py      # Config load/save
│       │   ├── models.py       # Config dataclasses
│       │   └── setup.py        # Interactive setup
│       ├── k8s/
│       │   ├── __init__.py
│       │   ├── client.py       # K8s client wrapper
│       │   ├── detection.py    # Auto-detection logic
│       │   └── queries.py      # Pod/event queries
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── configure.py
│       │   ├── runtime.py
│       │   ├── health.py
│       │   ├── list.py
│       │   ├── app.py
│       │   └── watch.py
│       └── output/
│           ├── __init__.py
│           ├── formatters.py   # JSON, table, text
│           └── recommendations.py
└── tests/
    └── ...
```

### Distribution

- PyPI package: `oh-debug` or `openhands-debug`
- Install: `pip install oh-debug`
- Or: `pipx install oh-debug`

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

1. **Naming**: `oh-debug`, `openhands-debug`, `ohd`, or something else?
2. **Should we support `--kubeconfig` override** for non-standard kubeconfig locations?
3. **Caching**: Should we cache cluster info to speed up repeated queries?
4. **Authentication**: Any special handling needed for GKE/EKS auth token refresh?

---

## References

- [runtime-api repository](https://github.com/OpenHands/runtime-api) - Runtime pod management
- [OpenHands repository](https://github.com/OpenHands/OpenHands) - Main application
- [OpenHands-Cloud repository](https://github.com/All-Hands-AI/OpenHands-Cloud) - Helm charts and deployment
