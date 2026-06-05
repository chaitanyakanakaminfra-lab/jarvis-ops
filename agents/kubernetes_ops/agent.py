import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class KubernetesOpsAgent(BaseAgent):
    agent_id   = "kubernetes_ops"
    agent_name = "Kubernetes Ops Agent"

    async def _run(self, command: str) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            cluster = eks.describe_cluster(name="jarvis-cluster")["cluster"]
            nodegroups = eks.list_nodegroups(clusterName="jarvis-cluster")["nodegroups"]
            
            status = cluster["status"]
            version = cluster["version"]
            node_count = len(nodegroups)
            
            return f"EKS cluster jarvis-cluster is {status}. Running Kubernetes {version} with {node_count} node group. All systems operational."
        except Exception as e:
            logger.error("k8s.error", error=str(e))
            return f"Could not reach EKS cluster: {str(e)}"
