import boto3
import structlog
from datetime import datetime, timezone
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class ReleaseVersioningAgent(BaseAgent):
    agent_id   = "release_versioning"
    agent_name = "Release & Versioning Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["latest", "current", "version", "show", "list"]):
                return await self._get_latest_versions()
            if any(w in cmd for w in ["history", "all releases"]):
                return await self._get_release_history()
            return await self._get_latest_versions()
        except Exception as e:
            return f"Release check failed: {str(e)}"

    async def _get_latest_versions(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            versions = []
            for repo in repos:
                try:
                    images = ecr.describe_images(
                        repositoryName=repo["repositoryName"],
                        filter={"tagStatus": "TAGGED"}
                    )["imageDetails"]
                    if images:
                        latest = max(images, key=lambda x: x.get("imagePushedAt",
                            datetime.min.replace(tzinfo=timezone.utc)))
                        tags = latest.get("imageTags", ["untagged"])
                        version_tags = [t for t in tags if t != "latest"]
                        tag = version_tags[0] if version_tags else tags[0]
                        size_mb = latest.get("imageSizeInBytes", 0) / (1024*1024)
                        pushed = latest["imagePushedAt"].strftime("%Y-%m-%d")
                        versions.append(f"{repo['repositoryName']}:{tag} ({size_mb:.0f}MB, {pushed})")
                except:
                    pass
            if versions:
                return f"Current releases ({len(versions)} total): {', '.join(versions)}. All versions healthy."
            return "No tagged releases found in ECR."
        except Exception as e:
            return f"Release check error: {str(e)}"

    async def _get_release_history(self) -> str:
        try:
            ecr = boto3.client("ecr", region_name="us-east-1")
            repos = ecr.describe_repositories()["repositories"]
            total = 0
            for repo in repos:
                try:
                    images = ecr.describe_images(repositoryName=repo["repositoryName"])["imageDetails"]
                    total += len(images)
                except:
                    pass
            return f"Release history: {len(repos)} repositories, {total} total image versions tracked."
        except Exception as e:
            return f"Release history error: {str(e)}"
