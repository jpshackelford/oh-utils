"""Kubernetes client wrapper for debug CLI."""

from typing import Any, Dict, List, Optional

from kubernetes import client, config
from kubernetes.client import ApiException
from kubernetes.config import ConfigException


class K8sClientError(Exception):
    """Exception raised for Kubernetes client errors."""

    pass


class K8sClient:
    """
    Wrapper for Kubernetes client operations.

    Handles context switching and provides simplified access to common operations.
    """

    def __init__(self, context: Optional[str] = None) -> None:
        """
        Initialize Kubernetes client.

        Args:
            context: Kubernetes context to use. If None, uses current context.
        """
        self.context = context
        self._core_api: Optional[client.CoreV1Api] = None
        self._apps_api: Optional[client.AppsV1Api] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load kubernetes configuration."""
        try:
            if self.context:
                config.load_kube_config(context=self.context)
            else:
                config.load_kube_config()
        except ConfigException as e:
            raise K8sClientError(f"Failed to load kube config: {e}") from e

    @property
    def core_api(self) -> client.CoreV1Api:
        """Get CoreV1Api client, creating if necessary."""
        if self._core_api is None:
            self._core_api = client.CoreV1Api()
        return self._core_api

    @property
    def apps_api(self) -> client.AppsV1Api:
        """Get AppsV1Api client, creating if necessary."""
        if self._apps_api is None:
            self._apps_api = client.AppsV1Api()
        return self._apps_api

    @staticmethod
    def list_contexts() -> List[Dict[str, Any]]:
        """List all available kubectl contexts."""
        try:
            contexts, active_context = config.list_kube_config_contexts()
            return [
                {
                    "name": ctx["name"],
                    "cluster": ctx["context"].get("cluster", ""),
                    "user": ctx["context"].get("user", ""),
                    "namespace": ctx["context"].get("namespace", "default"),
                    "active": ctx["name"] == active_context["name"],
                }
                for ctx in contexts
            ]
        except ConfigException:
            return []

    def get_namespaces(self) -> List[str]:
        """List all namespaces in the cluster."""
        try:
            result = self.core_api.list_namespace()
            return [ns.metadata.name for ns in result.items]
        except ApiException as e:
            raise K8sClientError(f"Failed to list namespaces: {e}") from e

    def get_deployment(
        self, name: str, namespace: str
    ) -> Optional[Dict[str, Any]]:
        """Get a deployment by name."""
        try:
            dep = self.apps_api.read_namespaced_deployment(name, namespace)
            return self._deployment_to_dict(dep)
        except ApiException as e:
            if e.status == 404:
                return None
            raise K8sClientError(f"Failed to get deployment {name}: {e}") from e

    def list_deployments(self, namespace: str) -> List[Dict[str, Any]]:
        """List all deployments in a namespace."""
        try:
            result = self.apps_api.list_namespaced_deployment(namespace)
            return [self._deployment_to_dict(dep) for dep in result.items]
        except ApiException as e:
            raise K8sClientError(f"Failed to list deployments: {e}") from e

    def get_deployment_env_vars(
        self, name: str, namespace: str, container_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Get environment variables from a deployment's containers."""
        dep = self.get_deployment(name, namespace)
        if not dep:
            return {}

        env_vars: Dict[str, str] = {}
        containers = dep.get("containers", [])

        for container in containers:
            if container_name and container["name"] != container_name:
                continue
            for env in container.get("env", []):
                if env.get("value"):
                    env_vars[env["name"]] = env["value"]

        return env_vars

    def get_pod(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        """Get a pod by name."""
        try:
            pod = self.core_api.read_namespaced_pod(name, namespace)
            return self._pod_to_dict(pod)
        except ApiException as e:
            if e.status == 404:
                return None
            raise K8sClientError(f"Failed to get pod {name}: {e}") from e

    def list_pods(
        self,
        namespace: str,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List pods in a namespace with optional selectors."""
        try:
            kwargs: Dict[str, Any] = {"namespace": namespace}
            if label_selector:
                kwargs["label_selector"] = label_selector
            if field_selector:
                kwargs["field_selector"] = field_selector

            result = self.core_api.list_namespaced_pod(**kwargs)
            return [self._pod_to_dict(pod) for pod in result.items]
        except ApiException as e:
            raise K8sClientError(f"Failed to list pods: {e}") from e

    def get_pod_logs(
        self,
        name: str,
        namespace: str,
        container: Optional[str] = None,
        previous: bool = False,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
    ) -> str:
        """Get logs from a pod."""
        try:
            kwargs: Dict[str, Any] = {
                "name": name,
                "namespace": namespace,
                "previous": previous,
            }
            if container:
                kwargs["container"] = container
            if tail_lines:
                kwargs["tail_lines"] = tail_lines
            if since_seconds:
                kwargs["since_seconds"] = since_seconds

            result: str = self.core_api.read_namespaced_pod_log(**kwargs)
            return result
        except ApiException as e:
            raise K8sClientError(f"Failed to get pod logs: {e}") from e

    def get_events(
        self,
        namespace: str,
        field_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get events in a namespace."""
        try:
            kwargs: Dict[str, Any] = {"namespace": namespace}
            if field_selector:
                kwargs["field_selector"] = field_selector

            result = self.core_api.list_namespaced_event(**kwargs)
            return [self._event_to_dict(event) for event in result.items]
        except ApiException as e:
            raise K8sClientError(f"Failed to get events: {e}") from e

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get all cluster nodes."""
        try:
            result = self.core_api.list_node()
            return [self._node_to_dict(node) for node in result.items]
        except ApiException as e:
            raise K8sClientError(f"Failed to list nodes: {e}") from e

    def _deployment_to_dict(self, dep: Any) -> Dict[str, Any]:
        """Convert deployment object to dictionary."""
        containers = []
        if dep.spec.template.spec.containers:
            for c in dep.spec.template.spec.containers:
                container_info: Dict[str, Any] = {
                    "name": c.name,
                    "image": c.image,
                    "env": [],
                    "resources": {},
                }
                if c.env:
                    container_info["env"] = [
                        {"name": e.name, "value": e.value} for e in c.env
                    ]
                if c.resources:
                    container_info["resources"] = {
                        "requests": dict(c.resources.requests or {}),
                        "limits": dict(c.resources.limits or {}),
                    }
                containers.append(container_info)

        return {
            "name": dep.metadata.name,
            "namespace": dep.metadata.namespace,
            "replicas": dep.spec.replicas,
            "ready_replicas": dep.status.ready_replicas or 0,
            "available_replicas": dep.status.available_replicas or 0,
            "containers": containers,
            "labels": dict(dep.metadata.labels or {}),
        }

    def _pod_to_dict(self, pod: Any) -> Dict[str, Any]:
        """Convert pod object to dictionary."""
        container_statuses = []
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                status_info: Dict[str, Any] = {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": "unknown",
                    "last_state": None,
                }

                if cs.state:
                    if cs.state.running:
                        status_info["state"] = "running"
                        status_info["started_at"] = (
                            cs.state.running.started_at.isoformat()
                            if cs.state.running.started_at
                            else None
                        )
                    elif cs.state.waiting:
                        status_info["state"] = "waiting"
                        status_info["reason"] = cs.state.waiting.reason
                        status_info["message"] = cs.state.waiting.message
                    elif cs.state.terminated:
                        status_info["state"] = "terminated"
                        status_info["reason"] = cs.state.terminated.reason
                        status_info["exit_code"] = cs.state.terminated.exit_code

                if cs.last_state and cs.last_state.terminated:
                    status_info["last_state"] = {
                        "state": "terminated",
                        "reason": cs.last_state.terminated.reason,
                        "exit_code": cs.last_state.terminated.exit_code,
                        "finished_at": (
                            cs.last_state.terminated.finished_at.isoformat()
                            if cs.last_state.terminated.finished_at
                            else None
                        ),
                    }

                container_statuses.append(status_info)

        resources: Dict[str, Any] = {"requests": {}, "limits": {}}
        if pod.spec.containers:
            for c in pod.spec.containers:
                if c.resources:
                    if c.resources.requests:
                        resources["requests"].update(c.resources.requests)
                    if c.resources.limits:
                        resources["limits"].update(c.resources.limits)

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "node_name": pod.spec.node_name,
            "created_at": (
                pod.metadata.creation_timestamp.isoformat()
                if pod.metadata.creation_timestamp
                else None
            ),
            "labels": dict(pod.metadata.labels or {}),
            "container_statuses": container_statuses,
            "resources": resources,
        }

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert event object to dictionary."""
        return {
            "name": event.metadata.name,
            "namespace": event.metadata.namespace,
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "count": event.count,
            "first_timestamp": (
                event.first_timestamp.isoformat() if event.first_timestamp else None
            ),
            "last_timestamp": (
                event.last_timestamp.isoformat() if event.last_timestamp else None
            ),
            "involved_object": {
                "kind": event.involved_object.kind,
                "name": event.involved_object.name,
                "namespace": event.involved_object.namespace,
            },
        }

    def _node_to_dict(self, node: Any) -> Dict[str, Any]:
        """Convert node object to dictionary."""
        conditions = {}
        if node.status.conditions:
            for cond in node.status.conditions:
                conditions[cond.type] = {
                    "status": cond.status,
                    "reason": cond.reason,
                    "message": cond.message,
                }

        allocatable = dict(node.status.allocatable or {})
        capacity = dict(node.status.capacity or {})

        return {
            "name": node.metadata.name,
            "labels": dict(node.metadata.labels or {}),
            "conditions": conditions,
            "allocatable": allocatable,
            "capacity": capacity,
        }
