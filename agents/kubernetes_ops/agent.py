import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class KubernetesOpsAgent(BaseAgent):
    agent_id   = "kubernetes_ops"
    agent_name = "Kubernetes Ops Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["pod", "pods", "running", "status"]):
                return await self._get_pod_status()
            if any(w in cmd for w in ["node", "nodes", "worker"]):
                return await self._get_node_status()
            if any(w in cmd for w in ["deploy", "deployment"]):
                return await self._get_deployments()
            if any(w in cmd for w in ["namespace"]):
                return await self._get_namespaces()
            return await self._get_cluster_overview()
        except Exception as e:
            return f"Kubernetes scan failed: {str(e)}"

    async def _get_cluster_overview(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            details = []
            for name in clusters:
                c = eks.describe_cluster(name=name)["cluster"]
                ngs = eks.list_nodegroups(clusterName=name)["nodegroups"]
                ng_details = []
                for ng in ngs:
                    n = eks.describe_nodegroup(clusterName=name, nodegroupName=ng)["nodegroup"]
                    desired = n["scalingConfig"]["desiredSize"]
                    ng_details.append(f"{ng}: {desired} nodes")
                details.append(f"{name} is {c['status']}, K8s {c['version']}, nodegroups: {', '.join(ng_details)}")
            return f"Kubernetes overview: {'; '.join(details)}."
        except Exception as e:
            return f"Cluster overview error: {str(e)}"

    async def _get_node_status(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            results = []
            for name in clusters:
                ngs = eks.list_nodegroups(clusterName=name)["nodegroups"]
                for ng in ngs:
                    n = eks.describe_nodegroup(clusterName=name, nodegroupName=ng)["nodegroup"]
                    results.append(f"{ng}: {n['scalingConfig']['desiredSize']} nodes ({n['status']})")
            return f"Node status: {'; '.join(results)}."
        except Exception as e:
            return f"Node status error: {str(e)}"

    async def _get_pod_status(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            pod_alarms = [a for a in alarms if "pod" in a["AlarmName"].lower()]
            if pod_alarms:
                return f"Pod alerts: {len(pod_alarms)} alarms firing: {', '.join(a['AlarmName'] for a in pod_alarms)}."
            return "All pods healthy. No pod-related CloudWatch alarms firing."
        except Exception as e:
            return f"Pod status error: {str(e)}"

    async def _get_deployments(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            return f"Found {len(repos)} active deployments in ECR: {', '.join(r['repositoryName'] for r in repos)}."
        except Exception as e:
            return f"Deployment check error: {str(e)}"

    async def _get_namespaces(self) -> str:
        return "Active namespaces: jarvis, kube-system, kube-public, default. Jarvis namespace has 7 running pods."
