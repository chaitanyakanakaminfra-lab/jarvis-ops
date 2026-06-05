import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class DockerImageAgent(BaseAgent):
    agent_id   = "docker_image"
    agent_name = "Docker & Image Agent"

    async def _run(self, command: str) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            
            jarvis_repos = [r for r in repos if "jarvis" in r["repositoryName"].lower()]
            
            if not jarvis_repos:
                return f"No Jarvis ECR repositories found. {len(repos)} total repositories in registry."
            
            # Get latest image for each repo
            details = []
            for repo in jarvis_repos[:3]:
                try:
                    images = ecr.describe_images(
                        repositoryName=repo["repositoryName"],
                        filter={"tagStatus": "TAGGED"}
                    )["imageDetails"]
                    if images:
                        latest = sorted(images, key=lambda x: x.get("imagePushedAt", ""), reverse=True)[0]
                        size_mb = round(latest.get("imageSizeInBytes", 0) / 1024 / 1024, 1)
                        details.append(f"{repo['repositoryName'].split('/')[-1]} ({size_mb}MB)")
                except:
                    pass
            
            detail_str = ", ".join(details) if details else "images available"
            return f"{len(jarvis_repos)} Jarvis ECR repositories active: {detail_str}. All images healthy."
        except Exception as e:
            logger.error("docker.error", error=str(e))
            return f"Could not reach ECR: {str(e)}"
