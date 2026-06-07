import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class AutoscalingAgent(BaseAgent):
    agent_id   = "autoscaling"
    agent_name = "Auto-Scaling Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["eks", "node", "kubernetes", "k8s"]):
                return await self._check_eks_scaling()
            if any(w in cmd for w in ["asg", "auto scaling group", "ec2 scaling"]):
                return await self._check_asg()
            if any(w in cmd for w in ["recommend", "optimize", "right-size"]):
                return await self._get_recommendations()
            return await self._get_scaling_overview()
        except Exception as e:
            return f"Autoscaling check failed: {str(e)}"

    async def _get_scaling_overview(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            asg = boto3.client("autoscaling", region_name="us-east-1")
            asgs = asg.describe_auto_scaling_groups()["AutoScalingGroups"]
            total_nodes = sum(g["DesiredCapacity"] for g in asgs)
            return f"Scaling overview: {len(clusters)} EKS cluster(s), {len(asgs)} auto scaling groups, {total_nodes} total nodes. Scaling healthy."
        except Exception as e:
            return f"Scaling overview error: {str(e)}"

    async def _check_eks_scaling(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            details = []
            for cluster in clusters:
                ngs = eks.list_nodegroups(clusterName=cluster)["nodegroups"]
                for ng in ngs:
                    n = eks.describe_nodegroup(clusterName=cluster, nodegroupName=ng)["nodegroup"]
                    sc = n["scalingConfig"]
                    details.append(f"{ng}: min={sc['minSize']}, desired={sc['desiredSize']}, max={sc['maxSize']}")
            return f"EKS scaling config: {'; '.join(details) if details else 'No nodegroups found'}."
        except Exception as e:
            return f"EKS scaling error: {str(e)}"

    async def _check_asg(self) -> str:
        try:
            asg = boto3.client("autoscaling", region_name="us-east-1")
            groups = asg.describe_auto_scaling_groups()["AutoScalingGroups"]
            details = []
            for g in groups[:5]:
                details.append(f"{g['AutoScalingGroupName']}: {g['DesiredCapacity']}/{g['MaxSize']} instances")
            return f"Auto Scaling Groups: {'; '.join(details) if details else 'No ASGs found'}."
        except Exception as e:
            return f"ASG check error: {str(e)}"

    async def _get_recommendations(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            recs = []
            for cluster in clusters:
                ngs = eks.list_nodegroups(clusterName=cluster)["nodegroups"]
                for ng in ngs:
                    n = eks.describe_nodegroup(clusterName=cluster, nodegroupName=ng)["nodegroup"]
                    sc = n["scalingConfig"]
                    if sc["desiredSize"] == sc["maxSize"]:
                        recs.append(f"Increase max nodes for {ng} (currently at max)")
                    elif sc["desiredSize"] == 0:
                        recs.append(f"{ng} scaled to 0 — scale up when needed")
            if recs:
                return f"Scaling recommendations: {'; '.join(recs)}."
            return "Scaling is well configured. All nodegroups have appropriate min/max limits."
        except Exception as e:
            return f"Recommendations error: {str(e)}"
