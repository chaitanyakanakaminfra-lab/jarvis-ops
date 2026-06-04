"""
orchestrator/tools/github_tool.py
───────────────────────────────────
LangChain tool for GitHub API operations.

Interview explanation:
  "The GitHub tool handles all repo interactions — posting PR comments,
   getting PR details, creating releases, and triggering workflows.
   I use httpx instead of PyGithub because it's async-native and gives
   full control over the API calls without a heavy dependency."
"""

import httpx
import structlog
from config.settings import get_settings

logger = structlog.get_logger(__name__)


class GitHubTool:

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.org = self.settings.github_org
        self.repo = self.settings.github_repo

    async def get_pr(self, pr_number: int) -> dict:
        """Get PR details."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.org}/{self.repo}/pulls/{pr_number}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def post_pr_comment(self, pr_number: int, body: str) -> dict:
        """Post a comment on a PR."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/repos/{self.org}/{self.repo}/issues/{pr_number}/comments",
                headers=self.headers,
                json={"body": body},
            )
            response.raise_for_status()
            logger.info("github.comment_posted", pr=pr_number)
            return response.json()

    async def get_pr_files(self, pr_number: int) -> list:
        """Get list of files changed in a PR."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.org}/{self.repo}/pulls/{pr_number}/files",
                headers=self.headers,
            )
            response.raise_for_status()
            return [f["filename"] for f in response.json()]

    async def create_release(
        self,
        tag: str,
        name: str,
        body: str,
        draft: bool = False,
    ) -> dict:
        """Create a GitHub release."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/repos/{self.org}/{self.repo}/releases",
                headers=self.headers,
                json={
                    "tag_name": tag,
                    "name": name,
                    "body": body,
                    "draft": draft,
                    "prerelease": False,
                },
            )
            response.raise_for_status()
            logger.info("github.release_created", tag=tag)
            return response.json()

    async def get_latest_commits(self, branch: str = "main", count: int = 5) -> list:
        """Get latest commits on a branch."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.org}/{self.repo}/commits",
                headers=self.headers,
                params={"sha": branch, "per_page": count},
            )
            response.raise_for_status()
            return [
                {
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0],
                    "author": c["commit"]["author"]["name"],
                }
                for c in response.json()
            ]

    async def set_commit_status(
        self,
        sha: str,
        state: str,
        description: str,
        context: str = "jarvis/ci",
    ) -> dict:
        """
        Set a commit status (pending/success/failure/error).
        Shows as a check mark on the PR.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/repos/{self.org}/{self.repo}/statuses/{sha}",
                headers=self.headers,
                json={
                    "state": state,
                    "description": description,
                    "context": context,
                },
            )
            response.raise_for_status()
            logger.info("github.status_set", sha=sha[:7], state=state)
            return response.json()
