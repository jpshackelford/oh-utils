"""Auto-detection of runtime configuration from deployed OpenHands Enterprise."""

from dataclasses import dataclass
from typing import Optional

from .client import K8sClient, K8sClientError


@dataclass
class DetectedRuntimeConfig:
    """Result of runtime configuration auto-detection."""

    same_cluster: bool
    namespace: str
    kube_context: Optional[str] = None
    gcp_project: Optional[str] = None
    gcp_region: Optional[str] = None
    gke_cluster_name: Optional[str] = None
    aws_region: Optional[str] = None
    eks_cluster_name: Optional[str] = None

    def construct_gke_context(self) -> Optional[str]:
        """Construct GKE context name from detected settings."""
        if self.gcp_project and self.gcp_region and self.gke_cluster_name:
            return f"gke_{self.gcp_project}_{self.gcp_region}_{self.gke_cluster_name}"
        return None

    def get_description(self) -> str:
        """Get human-readable description of detected config."""
        if self.same_cluster:
            return f"Runtimes in same cluster, namespace '{self.namespace}'"
        else:
            parts = ["Runtimes in DIFFERENT cluster"]
            if self.gcp_project:
                parts.append(f"Project: {self.gcp_project}")
            if self.gcp_region or self.aws_region:
                parts.append(f"Region: {self.gcp_region or self.aws_region}")
            if self.gke_cluster_name or self.eks_cluster_name:
                parts.append(
                    f"Cluster: {self.gke_cluster_name or self.eks_cluster_name}"
                )
            parts.append(f"Namespace: {self.namespace}")
            return ", ".join(parts)


class RuntimeDetector:
    """Detects runtime configuration from deployed OpenHands Enterprise."""

    # Support both naming conventions used in different deployments
    RUNTIME_API_DEPLOYMENT_NAMES = ["openhands-runtime-api", "runtime-api"]
    ENV_VARS_TO_DETECT = [
        "RUNTIME_IN_SAME_CLUSTER",
        "K8S_NAMESPACE",
        "GKE_CLUSTER_NAME",
        "GCP_PROJECT",
        "GCP_REGION",
        "AWS_REGION",
        "CLUSTER_NAME",
    ]

    def __init__(self, client: K8sClient) -> None:
        """Initialize detector with K8s client."""
        self.client = client

    def _find_runtime_api_deployment_name(self, app_namespace: str) -> Optional[str]:
        """Find the actual runtime-api deployment name in the namespace."""
        for name in self.RUNTIME_API_DEPLOYMENT_NAMES:
            dep = self.client.get_deployment(name, app_namespace)
            if dep is not None:
                return name
        return None

    def detect(self, app_namespace: str) -> Optional[DetectedRuntimeConfig]:
        """
        Detect runtime configuration from runtime-api deployment.

        Args:
            app_namespace: Namespace where OpenHands Enterprise is deployed

        Returns:
            DetectedRuntimeConfig if detection successful, None otherwise
        """
        try:
            deployment_name = self._find_runtime_api_deployment_name(app_namespace)
            if not deployment_name:
                return None

            env_vars = self.client.get_deployment_env_vars(
                deployment_name, app_namespace
            )

            if not env_vars:
                return None

            same_cluster_str = env_vars.get("RUNTIME_IN_SAME_CLUSTER", "true")
            same_cluster = same_cluster_str.lower() in ("true", "1", "yes")

            namespace = env_vars.get("K8S_NAMESPACE", "runtime-pods")

            return DetectedRuntimeConfig(
                same_cluster=same_cluster,
                namespace=namespace,
                gcp_project=env_vars.get("GCP_PROJECT"),
                gcp_region=env_vars.get("GCP_REGION"),
                gke_cluster_name=env_vars.get("GKE_CLUSTER_NAME"),
                aws_region=env_vars.get("AWS_REGION"),
                eks_cluster_name=env_vars.get("CLUSTER_NAME"),
            )
        except K8sClientError:
            return None

    def find_runtime_api_deployment(self, app_namespace: str) -> bool:
        """Check if runtime-api deployment exists in the namespace."""
        return self._find_runtime_api_deployment_name(app_namespace) is not None

    def match_context_to_detected(
        self, detected: DetectedRuntimeConfig, available_contexts: list
    ) -> Optional[str]:
        """
        Try to match detected runtime settings to an available kubectl context.

        Args:
            detected: Detected runtime configuration
            available_contexts: List of available kubectl contexts

        Returns:
            Matching context name if found, None otherwise
        """
        if detected.same_cluster:
            return None  # Use same context as app

        gke_context = detected.construct_gke_context()
        if gke_context:
            for ctx in available_contexts:
                if ctx["name"] == gke_context:
                    return gke_context

        if detected.eks_cluster_name:
            for ctx in available_contexts:
                ctx_name: str = ctx["name"]
                if detected.eks_cluster_name in ctx_name:
                    return ctx_name

        return None
