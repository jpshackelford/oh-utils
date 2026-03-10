"""Query helpers for runtime pods and cluster health."""

import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .client import K8sClient, K8sClientError


@dataclass
class RuntimePod:
    """Information about a runtime pod."""

    name: str
    namespace: str
    runtime_id: str
    session_id: Optional[str]
    phase: str
    node_name: Optional[str]
    created_at: Optional[datetime]
    restart_count: int
    last_restart_reason: Optional[str]
    container_state: str
    container_reason: Optional[str]
    cpu_request: Optional[str]
    cpu_limit: Optional[str]
    memory_request: Optional[str]
    memory_limit: Optional[str]
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def is_oom_killed(self) -> bool:
        """Check if pod was OOMKilled."""
        return self.last_restart_reason == "OOMKilled"

    @property
    def has_errors(self) -> bool:
        """Check if pod is in error state."""
        return self.phase in ("Failed", "Unknown") or self.container_state in (
            "waiting",
            "terminated",
        )

    @property
    def age_display(self) -> str:
        """Get human-readable age."""
        if not self.created_at:
            return "unknown"

        now = datetime.now(timezone.utc)
        delta = now - self.created_at

        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m"
        else:
            return f"{delta.seconds}s"

    def status_display(self) -> str:
        """Get formatted status for display."""
        if self.phase == "Running" and self.container_state == "running":
            return "🟢 Running"
        elif self.phase == "Pending":
            return "🟡 Pending"
        elif self.phase == "Succeeded":
            return "✅ Completed"
        elif self.phase == "Failed" or self.container_state == "terminated":
            return "🔴 Error"
        elif self.container_state == "waiting":
            return f"🟡 {self.container_reason or 'Waiting'}"
        else:
            return f"⚪ {self.phase}"


@dataclass
class ClusterHealthSummary:
    """Summary of cluster health."""

    total_runtimes: int
    running_runtimes: int
    pending_runtimes: int
    error_runtimes: int
    oom_killed_count: int
    evicted_count: int
    failed_scheduling_count: int
    recent_events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def running_percentage(self) -> float:
        """Get percentage of running runtimes."""
        if self.total_runtimes == 0:
            return 0.0
        return (self.running_runtimes / self.total_runtimes) * 100

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return (
            self.error_runtimes > 0
            or self.oom_killed_count > 0
            or self.failed_scheduling_count > 0
        )


class RuntimeQuery:
    """Query helper for runtime pods and cluster health."""

    # Try multiple label selectors - different deployments may use different labels
    RUNTIME_LABEL_SELECTORS = [
        "app.kubernetes.io/managed-by=openhands",
        "runtime_id",  # Label exists (any value)
    ]

    def __init__(self, client: K8sClient) -> None:
        """Initialize with K8s client."""
        self.client = client

    def get_runtime_pod(self, runtime_id: str, namespace: str) -> Optional[RuntimePod]:
        """Get a specific runtime pod by ID."""
        pods = self.list_runtime_pods(namespace)
        for pod in pods:
            if pod.runtime_id == runtime_id or pod.name == runtime_id:
                return pod
            if pod.session_id and pod.session_id == runtime_id:
                return pod
        return None

    def list_runtime_pods(
        self,
        namespace: str,
        label_selector: Optional[str] = None,
    ) -> List[RuntimePod]:
        """List all runtime pods in a namespace."""
        if label_selector:
            # Use provided selector
            try:
                pods = self.client.list_pods(namespace, label_selector=label_selector)
                return [self._pod_to_runtime(p) for p in pods]
            except K8sClientError:
                pass

        # Try each known label selector until we find runtime pods
        for selector in self.RUNTIME_LABEL_SELECTORS:
            try:
                pods = self.client.list_pods(namespace, label_selector=selector)
                if pods:  # Found some pods with this selector
                    return [self._pod_to_runtime(p) for p in pods]
            except K8sClientError:
                continue

        # Fallback: list all pods and filter by name/labels
        try:
            pods = self.client.list_pods(namespace)
            runtime_pods = [p for p in pods if self._looks_like_runtime(p)]
            return [self._pod_to_runtime(p) for p in runtime_pods]
        except K8sClientError:
            return []

    def list_runtime_pods_with_issues(self, namespace: str) -> List[RuntimePod]:
        """List runtime pods with errors or restarts."""
        pods = self.list_runtime_pods(namespace)
        return [p for p in pods if p.has_errors or p.restart_count > 0]

    def list_oom_killed_runtimes(self, namespace: str) -> List[RuntimePod]:
        """List runtime pods that were OOMKilled."""
        pods = self.list_runtime_pods(namespace)
        return [p for p in pods if p.is_oom_killed]

    def list_runtimes_with_restarts(
        self, namespace: str, min_restarts: int = 1
    ) -> List[RuntimePod]:
        """List runtime pods with at least min_restarts restarts."""
        pods = self.list_runtime_pods(namespace)
        return [p for p in pods if p.restart_count >= min_restarts]

    def get_pod_events(self, pod_name: str, namespace: str) -> List[Dict[str, Any]]:
        """Get events for a specific pod."""
        field_selector = f"involvedObject.name={pod_name}"
        events = self.client.get_events(namespace, field_selector=field_selector)
        return sorted(events, key=lambda e: e.get("last_timestamp") or "", reverse=True)

    def get_cluster_health(self, namespace: str) -> ClusterHealthSummary:
        """Get cluster health summary for runtime namespace."""
        pods = self.list_runtime_pods(namespace)

        running = sum(
            1 for p in pods if p.phase == "Running" and p.container_state == "running"
        )
        pending = sum(1 for p in pods if p.phase == "Pending")
        errors = sum(1 for p in pods if p.has_errors)
        oom_killed = sum(1 for p in pods if p.is_oom_killed)

        # Get recent events
        try:
            events = self.client.get_events(namespace)
            # Filter to warning events
            warning_events = [e for e in events if e.get("type") == "Warning"]
            # Sort by timestamp and take recent ones
            warning_events.sort(
                key=lambda e: e.get("last_timestamp") or "", reverse=True
            )
            recent_events = warning_events[:10]
        except K8sClientError:
            recent_events = []

        evicted = sum(1 for e in recent_events if e.get("reason") == "Evicted")
        failed_scheduling = sum(
            1 for e in recent_events if e.get("reason") == "FailedScheduling"
        )

        return ClusterHealthSummary(
            total_runtimes=len(pods),
            running_runtimes=running,
            pending_runtimes=pending,
            error_runtimes=errors,
            oom_killed_count=oom_killed,
            evicted_count=evicted,
            failed_scheduling_count=failed_scheduling,
            recent_events=recent_events,
        )

    def _looks_like_runtime(self, pod: Dict[str, Any]) -> bool:
        """Check if a pod looks like a runtime pod."""
        name = pod.get("name", "")
        labels = pod.get("labels", {})

        # Check for common runtime naming patterns
        if "runtime" in name.lower():
            return True

        # Check for OpenHands labels
        if labels.get("app.kubernetes.io/managed-by") == "openhands":
            return True

        return bool(labels.get("openhands.ai/runtime"))

    def _pod_to_runtime(self, pod: Dict[str, Any]) -> RuntimePod:
        """Convert pod dict to RuntimePod."""
        labels = pod.get("labels", {})
        container_statuses = pod.get("container_statuses", [])

        # Extract runtime ID from labels or name
        runtime_id = labels.get("openhands.ai/runtime-id") or pod["name"]
        session_id = labels.get("openhands.ai/session-id")

        # Get container status info
        restart_count = 0
        last_restart_reason = None
        container_state = "unknown"
        container_reason = None

        if container_statuses:
            cs = container_statuses[0]
            restart_count = cs.get("restart_count", 0)
            container_state = cs.get("state", "unknown")
            container_reason = cs.get("reason")

            if cs.get("last_state"):
                last_state = cs["last_state"]
                if last_state.get("state") == "terminated":
                    last_restart_reason = last_state.get("reason")

        # Get resource info
        resources = pod.get("resources", {})
        requests = resources.get("requests", {})
        limits = resources.get("limits", {})

        # Parse created_at
        created_at = None
        if pod.get("created_at"):
            with contextlib.suppress(ValueError, AttributeError):
                created_at = datetime.fromisoformat(
                    pod["created_at"].replace("Z", "+00:00")
                )

        return RuntimePod(
            name=pod["name"],
            namespace=pod["namespace"],
            runtime_id=runtime_id,
            session_id=session_id,
            phase=pod.get("phase", "Unknown"),
            node_name=pod.get("node_name"),
            created_at=created_at,
            restart_count=restart_count,
            last_restart_reason=last_restart_reason,
            container_state=container_state,
            container_reason=container_reason,
            cpu_request=requests.get("cpu"),
            cpu_limit=limits.get("cpu"),
            memory_request=requests.get("memory"),
            memory_limit=limits.get("memory"),
            labels=labels,
        )
