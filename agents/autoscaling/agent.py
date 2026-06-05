import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class AutoScalingAgent(BaseAgent):
    agent_id   = "autoscaling"
    agent_name = "Auto-Scaling Agent"

    async def _run(self, command: str) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            nodegroups = eks.list_nodegroups(clusterName="jarvis-cluster")["nodegroups"]
            
            details = []
            for ng in nodegroups:
                info = eks.describe_nodegroup(
                    clusterName="jarvis-cluster",
                    nodegroupName=ng
                )["nodegroup"]
                scaling = info["scalingConfig"]
                status = info["status"]
                details.append(f"{ng}: {scaling['desiredSize']} nodes (min {scaling['minSize']}, max {scaling['maxSize']}) - {status}")
            
            if details:
                return f"EKS scaling config: {'. '.join(details)}."
            return "No node groups found in jarvis-cluster."
        except Exception as e:
            logger.error("autoscaling.error", error=str(e))
            return f"Could not get scaling status: {str(e)}"
