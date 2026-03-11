"""Auto-detection of runtime configuration from deployed OpenHands Enterprise."""

from dataclasses import dataclass
from typing import List, Optional

from .client import K8sClient, K8sClientError


@dataclass
class DetectedAppEndpoint:
    """Result of application endpoint auto-detection."""

    host: str
    use_tls: bool
    source: str  # e.g., "env:WEB_HOST", "ingress:openhands-root-ingress"

    @property
    def url(self) -> str:
        """Get the full URL for the endpoint."""
        scheme = "https" if self.use_tls else "http"
        return f"{scheme}://{self.host}"


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
    # Runtime URL routing configuration
    runtime_url_pattern: Optional[str] = None  # e.g., "https://server/{runtime_id}"
    runtime_routing_mode: Optional[str] = None  # "path" or "subdomain"
    runtime_base_url: Optional[str] = None  # e.g., "runtime.example.com"

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

    def get_routing_description(self) -> Optional[str]:
        """Get human-readable description of runtime URL routing config."""
        if not self.runtime_url_pattern and not self.runtime_routing_mode:
            return None

        parts = []
        if self.runtime_routing_mode:
            parts.append(f"Mode: {self.runtime_routing_mode}")
        if self.runtime_url_pattern:
            parts.append(f"Pattern: {self.runtime_url_pattern}")
        elif self.runtime_base_url:
            parts.append(f"Base URL: {self.runtime_base_url}")
        return ", ".join(parts) if parts else None


class RuntimeDetector:
    """Detects runtime configuration from deployed OpenHands Enterprise."""

    # Support both naming conventions used in different deployments
    RUNTIME_API_DEPLOYMENT_NAMES = ["openhands-runtime-api", "runtime-api"]
    APP_DEPLOYMENT_NAMES = ["openhands", "openhands-server", "app"]

    # Env vars to detect from runtime-api deployment
    RUNTIME_API_ENV_VARS = [
        "RUNTIME_IN_SAME_CLUSTER",
        "K8S_NAMESPACE",
        "GKE_CLUSTER_NAME",
        "GCP_PROJECT",
        "GCP_REGION",
        "AWS_REGION",
        "CLUSTER_NAME",
        # Routing configuration
        "RUNTIME_BASE_URL",
        "RUNTIME_ROUTING_MODE",
        "RUNTIME_URL_SEPARATOR",
    ]

    # Env vars to detect from app deployment (for URL pattern)
    APP_ENV_VARS = [
        "RUNTIME_URL_PATTERN",
        "RUNTIME_ROUTING_MODE",
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

    def _find_app_deployment_name(self, app_namespace: str) -> Optional[str]:
        """Find the actual app deployment name in the namespace."""
        for name in self.APP_DEPLOYMENT_NAMES:
            dep = self.client.get_deployment(name, app_namespace)
            if dep is not None:
                return name
        return None

    def _get_app_env_vars(self, app_namespace: str) -> dict:
        """Get environment variables from the app deployment."""
        app_deployment = self._find_app_deployment_name(app_namespace)
        if not app_deployment:
            return {}
        try:
            return self.client.get_deployment_env_vars(app_deployment, app_namespace)
        except K8sClientError:
            return {}

    def detect(self, app_namespace: str) -> Optional[DetectedRuntimeConfig]:
        """
        Detect runtime configuration from runtime-api and app deployments.

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

            # Get routing config from runtime-api deployment
            runtime_base_url = env_vars.get("RUNTIME_BASE_URL")
            runtime_routing_mode = env_vars.get("RUNTIME_ROUTING_MODE")

            # Also check app deployment for RUNTIME_URL_PATTERN
            # (this is where it's typically set in helm values)
            app_env_vars = self._get_app_env_vars(app_namespace)
            runtime_url_pattern = app_env_vars.get("RUNTIME_URL_PATTERN")

            # App deployment may also have RUNTIME_ROUTING_MODE
            if not runtime_routing_mode:
                runtime_routing_mode = app_env_vars.get("RUNTIME_ROUTING_MODE")

            return DetectedRuntimeConfig(
                same_cluster=same_cluster,
                namespace=namespace,
                gcp_project=env_vars.get("GCP_PROJECT"),
                gcp_region=env_vars.get("GCP_REGION"),
                gke_cluster_name=env_vars.get("GKE_CLUSTER_NAME"),
                aws_region=env_vars.get("AWS_REGION"),
                eks_cluster_name=env_vars.get("CLUSTER_NAME"),
                runtime_url_pattern=runtime_url_pattern,
                runtime_routing_mode=runtime_routing_mode,
                runtime_base_url=runtime_base_url,
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


class AppEndpointDetector:
    """Detects application endpoint from deployed OpenHands Enterprise."""

    # Deployment names to check for WEB_HOST env var (in order of preference)
    APP_DEPLOYMENT_NAMES = ["openhands", "openhands-server", "app"]

    # Ingress names that typically point to the main app (in order of preference)
    APP_INGRESS_NAMES = [
        "openhands-root-ingress",
        "openhands-ingress",
        "openhands",
        "app-ingress",
    ]

    def __init__(self, client: K8sClient) -> None:
        """Initialize detector with K8s client."""
        self.client = client

    def detect(self, app_namespace: str) -> Optional[DetectedAppEndpoint]:
        """
        Detect application endpoint from cluster configuration.

        Tries multiple detection methods in order of reliability:
        1. WEB_HOST environment variable from openhands deployment
        2. Ingress host from openhands-root-ingress or similar

        Args:
            app_namespace: Namespace where OpenHands Enterprise is deployed

        Returns:
            DetectedAppEndpoint if detection successful, None otherwise
        """
        # Try env var detection first (most reliable)
        endpoint = self._detect_from_env_var(app_namespace)
        if endpoint:
            return endpoint

        # Fallback to ingress detection
        return self._detect_from_ingress(app_namespace)

    def _detect_from_env_var(self, namespace: str) -> Optional[DetectedAppEndpoint]:
        """Detect endpoint from WEB_HOST environment variable."""
        for deployment_name in self.APP_DEPLOYMENT_NAMES:
            try:
                env_vars = self.client.get_deployment_env_vars(
                    deployment_name, namespace
                )
                if not env_vars:
                    continue

                web_host = env_vars.get("WEB_HOST")
                if web_host:
                    # Check if TLS is likely (most deployments use TLS)
                    # Could also check for TLS-related env vars
                    use_tls = True  # Default to HTTPS
                    return DetectedAppEndpoint(
                        host=web_host,
                        use_tls=use_tls,
                        source=f"env:WEB_HOST (deployment: {deployment_name})",
                    )
            except K8sClientError:
                continue

        return None

    def _detect_from_ingress(self, namespace: str) -> Optional[DetectedAppEndpoint]:
        """Detect endpoint from ingress resources."""
        # Try known ingress names first
        for ingress_name in self.APP_INGRESS_NAMES:
            try:
                ingress = self.client.get_ingress(ingress_name, namespace)
                if ingress and ingress.get("hosts"):
                    host = ingress["hosts"][0]
                    # Check if TLS is configured
                    use_tls = host in ingress.get("tls_hosts", [])
                    return DetectedAppEndpoint(
                        host=host,
                        use_tls=use_tls,
                        source=f"ingress:{ingress_name}",
                    )
            except K8sClientError:
                continue

        # Fallback: search all ingresses for one that looks like the main app
        try:
            ingresses = self.client.list_ingresses(namespace)
            for ingress in ingresses:
                # Skip runtime ingresses
                name = ingress.get("name", "")
                if name.startswith("runtime-"):
                    continue

                # Look for ingress with "/" path (root ingress)
                # Prefer ingresses with 'openhands' in the name
                hosts = ingress.get("hosts", [])
                if hosts and ("openhands" in name.lower() or "root" in name.lower()):
                    host = hosts[0]
                    use_tls = host in ingress.get("tls_hosts", [])
                    return DetectedAppEndpoint(
                        host=host,
                        use_tls=use_tls,
                        source=f"ingress:{name}",
                    )
        except K8sClientError:
            pass

        return None

    def detect_all_endpoints(self, app_namespace: str) -> List[DetectedAppEndpoint]:
        """
        Detect all possible application endpoints.

        Useful for showing user all detected endpoints when there might be
        multiple (e.g., internal and external).

        Args:
            app_namespace: Namespace where OpenHands Enterprise is deployed

        Returns:
            List of all detected endpoints
        """
        endpoints: List[DetectedAppEndpoint] = []

        # Get from env var
        env_endpoint = self._detect_from_env_var(app_namespace)
        if env_endpoint:
            endpoints.append(env_endpoint)

        # Get from ingresses
        try:
            ingresses = self.client.list_ingresses(app_namespace)
            for ingress in ingresses:
                name = ingress.get("name", "")
                # Skip runtime ingresses
                if name.startswith("runtime-"):
                    continue

                hosts = ingress.get("hosts", [])
                for host in hosts:
                    # Skip if we already have this host
                    if any(e.host == host for e in endpoints):
                        continue

                    use_tls = host in ingress.get("tls_hosts", [])
                    endpoints.append(
                        DetectedAppEndpoint(
                            host=host,
                            use_tls=use_tls,
                            source=f"ingress:{name}",
                        )
                    )
        except K8sClientError:
            pass

        return endpoints
