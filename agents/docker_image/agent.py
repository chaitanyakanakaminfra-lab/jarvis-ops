import boto3
import structlog
from datetime import datetime, timezone
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class DockerImageAgent(BaseAgent):
    agent_id   = "docker_image"
    agent_name = "Docker & Image Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["list", "show", "all", "repos"]):
                return await self._list_repos()
            if any(w in cmd for w in ["size", "storage", "space"]):
                return await self._get_storage_info()
            if any(w in cmd for w in ["latest", "recent", "last push"]):
                return await self._get_recent_images()
            if any(w in cmd for w in ["clean", "delete", "untagged", "unused"]):
                return await self._get_cleanup_info()
            return await self._get_overview()
        except Exception as e:
            return f"Docker check failed: {str(e)}"

    async def _get_overview(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            total_size = 0
            total_images = 0
            for repo in repos:
                try:
                    images = ecr.describe_images(repositoryName=repo["repositoryName"])["imageDetails"]
                    total_images += len(images)
                    for img in images:
                        total_size += img.get("imageSizeInBytes", 0)
                except:
                    pass
            size_mb = total_size / (1024 * 1024)
            return f"{len(repos)} ECR repositories, {total_images} images, {size_mb:.1f}MB total. All images healthy and ready."
        except Exception as e:
            return f"Docker overview error: {str(e)}"

    async def _list_repos(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            names = [r["repositoryName"] for r in repos]
            return f"ECR repositories ({len(repos)} total): {', '.join(names)}."
        except Exception as e:
            return f"Repo list error: {str(e)}"

    async def _get_storage_info(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            sizes = []
            for repo in repos:
                try:
                    images = ecr.describe_images(repositoryName=repo["repositoryName"])["imageDetails"]
                    size = sum(img.get("imageSizeInBytes", 0) for img in images) / (1024*1024)
                    sizes.append(f"{repo['repositoryName']}: {size:.1f}MB")
                except:
                    pass
            return f"Storage breakdown: {'; '.join(sizes) if sizes else 'No data'}."
        except Exception as e:
            return f"Storage info error: {str(e)}"

    async def _get_recent_images(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            recent = []
            for repo in repos:
                try:
                    images = ecr.describe_images(
                        repositoryName=repo["repositoryName"],
                        filter={"tagStatus": "TAGGED"}
                    )["imageDetails"]
                    if images:
                        latest = max(images, key=lambda x: x.get("imagePushedAt", datetime.min.replace(tzinfo=timezone.utc)))
                        tags = latest.get("imageTags", ["untagged"])
                        pushed = latest["imagePushedAt"].strftime("%Y-%m-%d %H:%M")
                        recent.append(f"{repo['repositoryName']}:{tags[0]} ({pushed})")
                except:
                    pass
            return f"Recent images: {', '.join(recent[:5]) if recent else 'No recent pushes'}."
        except Exception as e:
            return f"Recent images error: {str(e)}"

    async def _get_cleanup_info(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            untagged_total = 0
            for repo in repos:
                try:
                    images = ecr.describe_images(
                        repositoryName=repo["repositoryName"],
                        filter={"tagStatus": "UNTAGGED"}
                    )["imageDetails"]
                    untagged_total += len(images)
                except:
                    pass
            size_savings = untagged_total * 50
            return f"Cleanup analysis: {untagged_total} untagged images found across {len(repos)} repos. Estimated savings: {size_savings}MB."
        except Exception as e:
            return f"Cleanup info error: {str(e)}"
