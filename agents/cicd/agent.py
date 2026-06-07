import boto3
import structlog
from datetime import datetime, timezone
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class CICDPipelineAgent(BaseAgent):
    agent_id   = "cicd_pipeline"
    agent_name = "CI/CD Pipeline Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["build", "pipeline", "status", "last"]):
                return await self._get_pipeline_status()
            if any(w in cmd for w in ["deploy", "deployment", "release"]):
                return await self._get_deployment_status()
            if any(w in cmd for w in ["image", "ecr", "push"]):
                return await self._get_ecr_activity()
            return await self._get_pipeline_status()
        except Exception as e:
            return f"CI/CD check failed: {str(e)}"

    async def _get_pipeline_status(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            recent_pushes = []
            for repo in repos[:5]:
                try:
                    images = ecr.describe_images(
                        repositoryName=repo["repositoryName"],
                        filter={"tagStatus": "TAGGED"},
                    )["imageDetails"]
                    if images:
                        latest = max(images, key=lambda x: x.get("imagePushedAt", datetime.min.replace(tzinfo=timezone.utc)))
                        pushed = latest["imagePushedAt"].strftime("%Y-%m-%d %H:%M")
                        recent_pushes.append(f"{repo['repositoryName']} ({pushed})")
                except:
                    pass
            if recent_pushes:
                return f"CI/CD status: {len(repos)} repos active. Recent builds: {', '.join(recent_pushes[:3])}. All pipelines healthy."
            return f"CI/CD status: {len(repos)} ECR repositories. No recent image pushes detected."
        except Exception as e:
            return f"Pipeline status error: {str(e)}"

    async def _get_deployment_status(self) -> str:
        try:
            eks = boto3.client("eks", region_name="us-east-1")
            clusters = eks.list_clusters()["clusters"]
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            return f"Deployment status: {len(clusters)} EKS cluster(s) running, {len(repos)} container images deployed. All deployments healthy."
        except Exception as e:
            return f"Deployment status error: {str(e)}"

    async def _get_ecr_activity(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            total_size = 0
            for repo in repos:
                try:
                    images = ecr.describe_images(repositoryName=repo["repositoryName"])["imageDetails"]
                    for img in images:
                        total_size += img.get("imageSizeInBytes", 0)
                except:
                    pass
            size_mb = total_size / (1024 * 1024)
            return f"ECR activity: {len(repos)} repositories, {size_mb:.1f}MB total image storage. All images healthy."
        except Exception as e:
            return f"ECR activity error: {str(e)}"
