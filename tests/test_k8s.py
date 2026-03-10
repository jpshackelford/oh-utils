"""Tests for Kubernetes client utilities."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from ohc.k8s.client import K8sClient, K8sClientError
from ohc.k8s.detection import DetectedRuntimeConfig, RuntimeDetector
from ohc.k8s.queries import ClusterHealthSummary, RuntimePod, RuntimeQuery


class TestDetectedRuntimeConfig:
    """Tests for DetectedRuntimeConfig."""

    def test_construct_gke_context(self) -> None:
        config = DetectedRuntimeConfig(
            same_cluster=False,
            namespace="runtime-pods",
            gcp_project="myproject",
            gcp_region="us-central1",
            gke_cluster_name="mycluster",
        )
        assert config.construct_gke_context() == "gke_myproject_us-central1_mycluster"

    def test_construct_gke_context_missing_values(self) -> None:
        config = DetectedRuntimeConfig(
            same_cluster=False,
            namespace="runtime-pods",
            gcp_project="myproject",
        )
        assert config.construct_gke_context() is None

    def test_get_description_same_cluster(self) -> None:
        config = DetectedRuntimeConfig(
            same_cluster=True,
            namespace="runtime-pods",
        )
        assert "same cluster" in config.get_description()
        assert "runtime-pods" in config.get_description()

    def test_get_description_different_cluster(self) -> None:
        config = DetectedRuntimeConfig(
            same_cluster=False,
            namespace="runtime-pods",
            gcp_project="myproject",
            gcp_region="us-central1",
            gke_cluster_name="mycluster",
        )
        desc = config.get_description()
        assert "DIFFERENT cluster" in desc
        assert "myproject" in desc


class TestRuntimeDetector:
    """Tests for RuntimeDetector."""

    def test_detect_same_cluster(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.get_deployment_env_vars.return_value = {
            "RUNTIME_IN_SAME_CLUSTER": "true",
            "K8S_NAMESPACE": "runtime-pods",
        }

        detector = RuntimeDetector(mock_client)
        result = detector.detect("openhands")

        assert result is not None
        assert result.same_cluster is True
        assert result.namespace == "runtime-pods"

    def test_detect_different_cluster_gke(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.get_deployment_env_vars.return_value = {
            "RUNTIME_IN_SAME_CLUSTER": "false",
            "K8S_NAMESPACE": "runtime-pods",
            "GCP_PROJECT": "myproject",
            "GCP_REGION": "us-west1",
            "GKE_CLUSTER_NAME": "runtime-cluster",
        }

        detector = RuntimeDetector(mock_client)
        result = detector.detect("openhands")

        assert result is not None
        assert result.same_cluster is False
        assert result.gcp_project == "myproject"
        assert result.gke_cluster_name == "runtime-cluster"

    def test_detect_no_deployment(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.get_deployment_env_vars.return_value = {}

        detector = RuntimeDetector(mock_client)
        result = detector.detect("openhands")

        assert result is None

    def test_detect_error(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.get_deployment_env_vars.side_effect = K8sClientError(
            "Connection failed"
        )

        detector = RuntimeDetector(mock_client)
        result = detector.detect("openhands")

        assert result is None

    def test_match_context_same_cluster(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        detector = RuntimeDetector(mock_client)

        detected = DetectedRuntimeConfig(same_cluster=True, namespace="runtime-pods")
        contexts = [{"name": "ctx1"}, {"name": "ctx2"}]

        result = detector.match_context_to_detected(detected, contexts)
        assert result is None

    def test_match_context_gke(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        detector = RuntimeDetector(mock_client)

        detected = DetectedRuntimeConfig(
            same_cluster=False,
            namespace="runtime-pods",
            gcp_project="myproject",
            gcp_region="us-west1",
            gke_cluster_name="runtime-cluster",
        )
        contexts = [
            {"name": "gke_myproject_us-west1_runtime-cluster"},
            {"name": "other-context"},
        ]

        result = detector.match_context_to_detected(detected, contexts)
        assert result == "gke_myproject_us-west1_runtime-cluster"


class TestRuntimePod:
    """Tests for RuntimePod dataclass."""

    def test_is_oom_killed(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Running",
            node_name=None,
            created_at=None,
            restart_count=1,
            last_restart_reason="OOMKilled",
            container_state="running",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert pod.is_oom_killed is True

    def test_is_not_oom_killed(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Running",
            node_name=None,
            created_at=None,
            restart_count=1,
            last_restart_reason="Error",
            container_state="running",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert pod.is_oom_killed is False

    def test_has_errors_failed_phase(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Failed",
            node_name=None,
            created_at=None,
            restart_count=0,
            last_restart_reason=None,
            container_state="terminated",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert pod.has_errors is True

    def test_has_errors_running(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Running",
            node_name=None,
            created_at=None,
            restart_count=0,
            last_restart_reason=None,
            container_state="running",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert pod.has_errors is False

    def test_age_display_days(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Running",
            node_name=None,
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            restart_count=0,
            last_restart_reason=None,
            container_state="running",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert "d" in pod.age_display

    def test_age_display_unknown(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Running",
            node_name=None,
            created_at=None,
            restart_count=0,
            last_restart_reason=None,
            container_state="running",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert pod.age_display == "unknown"

    def test_status_display_running(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Running",
            node_name=None,
            created_at=None,
            restart_count=0,
            last_restart_reason=None,
            container_state="running",
            container_reason=None,
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert "🟢" in pod.status_display()

    def test_status_display_pending(self) -> None:
        pod = RuntimePod(
            name="test-pod",
            namespace="runtime-pods",
            runtime_id="rt-123",
            session_id=None,
            phase="Pending",
            node_name=None,
            created_at=None,
            restart_count=0,
            last_restart_reason=None,
            container_state="waiting",
            container_reason="ContainerCreating",
            cpu_request=None,
            cpu_limit=None,
            memory_request=None,
            memory_limit=None,
        )
        assert "🟡" in pod.status_display()


class TestClusterHealthSummary:
    """Tests for ClusterHealthSummary."""

    def test_running_percentage(self) -> None:
        summary = ClusterHealthSummary(
            total_runtimes=100,
            running_runtimes=90,
            pending_runtimes=5,
            error_runtimes=5,
            oom_killed_count=2,
            evicted_count=0,
            failed_scheduling_count=0,
        )
        assert summary.running_percentage == 90.0

    def test_running_percentage_zero_total(self) -> None:
        summary = ClusterHealthSummary(
            total_runtimes=0,
            running_runtimes=0,
            pending_runtimes=0,
            error_runtimes=0,
            oom_killed_count=0,
            evicted_count=0,
            failed_scheduling_count=0,
        )
        assert summary.running_percentage == 0.0

    def test_has_issues_with_errors(self) -> None:
        summary = ClusterHealthSummary(
            total_runtimes=10,
            running_runtimes=9,
            pending_runtimes=0,
            error_runtimes=1,
            oom_killed_count=0,
            evicted_count=0,
            failed_scheduling_count=0,
        )
        assert summary.has_issues is True

    def test_has_issues_with_oom(self) -> None:
        summary = ClusterHealthSummary(
            total_runtimes=10,
            running_runtimes=10,
            pending_runtimes=0,
            error_runtimes=0,
            oom_killed_count=1,
            evicted_count=0,
            failed_scheduling_count=0,
        )
        assert summary.has_issues is True

    def test_no_issues(self) -> None:
        summary = ClusterHealthSummary(
            total_runtimes=10,
            running_runtimes=10,
            pending_runtimes=0,
            error_runtimes=0,
            oom_killed_count=0,
            evicted_count=0,
            failed_scheduling_count=0,
        )
        assert summary.has_issues is False


class TestRuntimeQuery:
    """Tests for RuntimeQuery."""

    def test_list_runtime_pods(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.list_pods.return_value = [
            {
                "name": "runtime-abc123",
                "namespace": "runtime-pods",
                "phase": "Running",
                "node_name": "node-1",
                "created_at": "2024-01-01T00:00:00Z",
                "labels": {
                    "app.kubernetes.io/managed-by": "openhands",
                    "openhands.ai/runtime-id": "abc123",
                },
                "container_statuses": [
                    {
                        "name": "runtime",
                        "ready": True,
                        "restart_count": 0,
                        "state": "running",
                    }
                ],
                "resources": {
                    "requests": {"cpu": "1000m", "memory": "2Gi"},
                    "limits": {"cpu": "2000m", "memory": "4Gi"},
                },
            }
        ]

        query = RuntimeQuery(mock_client)
        pods = query.list_runtime_pods("runtime-pods")

        assert len(pods) == 1
        assert pods[0].runtime_id == "abc123"
        assert pods[0].phase == "Running"

    def test_get_runtime_pod_by_id(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.list_pods.return_value = [
            {
                "name": "runtime-abc123",
                "namespace": "runtime-pods",
                "phase": "Running",
                "node_name": None,
                "created_at": None,
                "labels": {"openhands.ai/runtime-id": "abc123"},
                "container_statuses": [],
                "resources": {},
            }
        ]

        query = RuntimeQuery(mock_client)
        pod = query.get_runtime_pod("abc123", "runtime-pods")

        assert pod is not None
        assert pod.runtime_id == "abc123"

    def test_get_runtime_pod_not_found(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.list_pods.return_value = []

        query = RuntimeQuery(mock_client)
        pod = query.get_runtime_pod("nonexistent", "runtime-pods")

        assert pod is None

    def test_list_oom_killed_runtimes(self) -> None:
        mock_client = MagicMock(spec=K8sClient)
        mock_client.list_pods.return_value = [
            {
                "name": "runtime-1",
                "namespace": "runtime-pods",
                "phase": "Running",
                "node_name": None,
                "created_at": None,
                "labels": {"openhands.ai/runtime-id": "rt-1"},
                "container_statuses": [
                    {
                        "name": "runtime",
                        "ready": True,
                        "restart_count": 2,
                        "state": "running",
                        "last_state": {"state": "terminated", "reason": "OOMKilled"},
                    }
                ],
                "resources": {},
            },
            {
                "name": "runtime-2",
                "namespace": "runtime-pods",
                "phase": "Running",
                "node_name": None,
                "created_at": None,
                "labels": {"openhands.ai/runtime-id": "rt-2"},
                "container_statuses": [
                    {
                        "name": "runtime",
                        "ready": True,
                        "restart_count": 0,
                        "state": "running",
                    }
                ],
                "resources": {},
            },
        ]

        query = RuntimeQuery(mock_client)
        oom_pods = query.list_oom_killed_runtimes("runtime-pods")

        assert len(oom_pods) == 1
        assert oom_pods[0].runtime_id == "rt-1"
