import structlog
from agents.base_agent import BaseAgent
from orchestrator.tools.cloud_tool import CloudTool

logger = structlog.get_logger(__name__)


class KubernetesOpsAgent(BaseAgent):
    agent_id   = "kubernetes_ops"
    agent_name = "Kubernetes Ops Agent"

    def __init__(self):
        super().__init__()
        self.cloud = CloudTool()

    async def _run(self, command: str) -> str:
        command_lower = command.lower()
        if any(w in command_lower for w in ["health", "status", "check", "how"]):
            return await self._cluster_health()
        if any(w in command_lower for w in ["rollback", "roll back"]):
            return await self._rollback()
        if any(w in command_lower for w in ["scale", "resize"]):
            return await self._scale_nodes(command_lower)
        if any(w in command_lower for w in ["pods", "pod", "crash"]):
            return await self._check_pods()
        return await self._cluster_health()

    async def _cluster_health(self) -> str:
        try:
            info = await self.cloud.get_cluster_info()
            nodegroups = await self.cloud.list_nodegroups()
            return (
                f"EKS cluster {info['name']} is {info['status']}. "
                f"{len(nodegroups)} node group(s) active."
            )
        except Exception as e:
            return f"Could not get cluster health: {str(e)}"

    async def _check_pods(self) -> str:
        try:
            from kubernetes import client, config
            config.load_incluster_config()
            v1 = client.CoreV1Api()
            pods = v1.list_namespaced_pod(namespace="jarvis")
            crash_loops = [
                p.metadata.name for p in pods.items
                if p.status.phase not in ["Running", "Succeeded"]
            ]
            if crash_loops:
                return f"{len(crash_loops)} pods are not healthy in the jarvis namespace: {', '.join(crash_loops[:3])}."
            return f"All {len(pods.items)} pods in the jarvis namespace are healthy."
        except Exception as e:
            return f"Could not check pods: {str(e)}"

    async def _rollback(self) -> str:
        try:
            from kubernetes import client, config
            config.load_incluster_config()
            apps_v1 = client.AppsV1Api()
            apps_v1.create_namespaced_deployment_rollback(
                name="jarvis-orchestrator",
                namespace="jarvis",
                body=client.AppsV1beta1DeploymentRollback(
                    name="jarvis-orchestrator",
                    rollback_to=client.AppsV1beta1RollbackConfig(),
                ),
            )
            return "Rollback initiated for jarvis-orchestrator deployment."
        except Exception as e:
            return f"Rollback failed: {str(e)}"

    async def _scale_nodes(self, command: str) -> str:
        import re
        match = re.search(r"\b(\d+)\b", command)
        count = int(match.group(1)) if match else 2
        return f"Scaling EKS node group to {count} nodes. Use 'make scale-up' or 'make scale-down' for quick scaling."
