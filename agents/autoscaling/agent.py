import structlog
from agents.base_agent import BaseAgent
from orchestrator.tools.cloud_tool import CloudTool

logger = structlog.get_logger(__name__)


class AutoScalingAgent(BaseAgent):
    agent_id   = "autoscaling"
    agent_name = "Auto-Scaling Agent"

    def __init__(self):
        super().__init__()
        self.cloud = CloudTool()

    async def _run(self, command: str) -> str:
        import re
        command_lower = command.lower()
        match = re.search(r"\b(\d+)\b", command)
        count = int(match.group(1)) if match else None

        if any(w in command_lower for w in ["down", "reduce", "shrink", "less"]):
            target = count or 1
            return await self._scale(target, "down")
        if any(w in command_lower for w in ["up", "increase", "more", "grow"]):
            target = count or 3
            return await self._scale(target, "up")
        if any(w in command_lower for w in ["status", "current", "how many"]):
            return await self._scaling_status()
        return await self._scaling_status()

    async def _scale(self, count: int, direction: str) -> str:
        try:
            import boto3
            client = boto3.client("eks", region_name=self.settings.aws_default_region)
            client.update_nodegroup_config(
                clusterName="jarvis-cluster",
                nodegroupName="jarvis-nodes",
                scalingConfig={
                    "minSize": 0 if direction == "down" else 1,
                    "maxSize": max(count, 3),
                    "desiredSize": count,
                },
            )
            action = "scaled down" if direction == "down" else "scaled up"
            saving = " Saving approximately $1.90 per day." if direction == "down" and count == 0 else ""
            return f"EKS node group {action} to {count} nodes.{saving}"
        except Exception as e:
            return f"Scaling failed: {str(e)}"

    async def _scaling_status(self) -> str:
        try:
            nodegroups = await self.cloud.list_nodegroups()
            return f"EKS cluster has {len(nodegroups)} active node group(s). Use 'scale up' or 'scale down' to adjust."
        except Exception as e:
            return f"Could not get scaling status: {str(e)}"
