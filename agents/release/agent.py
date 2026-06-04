"""
agents/release/agent.py
────────────────────────
Release & Versioning Agent — semver tagging, changelogs, GitHub releases.

Interview explanation:
  "The release agent automates the full release process — it reads
   the latest commits, determines the version bump type using
   conventional commits (feat = minor, fix = patch, breaking = major),
   generates a changelog, creates a git tag, and publishes a GitHub
   release. All triggered by a voice command like 'cut a release'.

   This follows the conventional commits standard I use at IBM —
   feat:, fix:, chore:, refactor: prefixes drive automated versioning."
"""

import re
import structlog

from agents.base_agent import BaseAgent
from agents.release.voice_responses import (
    release_started, release_created, release_failed,
    changelog_generated, tag_created, tag_exists,
    version_bumped, no_changes_since_last_release,
    draft_release_created,
)
from orchestrator.tools.github_tool import GitHubTool

logger = structlog.get_logger(__name__)

# Conventional commit types → version bump
BUMP_RULES = {
    "major": ["breaking", "breaking change", "!:"],
    "minor": ["feat", "feature"],
    "patch": ["fix", "bugfix", "hotfix", "patch", "chore", "refactor", "docs"],
}


class ReleaseAgent(BaseAgent):

    agent_id   = "release_versioning"
    agent_name = "Release & Versioning Agent"

    def __init__(self):
        super().__init__()
        self.github = GitHubTool()

    async def _run(self, command: str) -> str:
        """
        Parse command and perform the right release operation.

        Examples:
          "cut a release"              → auto version bump + changelog + tag + release
          "create a patch release"     → patch bump
          "create a minor release"     → minor bump
          "tag version 2.5.0"          → create specific tag
          "generate changelog"         → changelog only
          "what is the latest version" → check current version
        """
        command_lower = command.lower()

        # ── Check current version ─────────────────────────────────────────────
        if any(w in command_lower for w in ["latest version", "current version", "what version"]):
            return await self._get_current_version()

        # ── Generate changelog only ───────────────────────────────────────────
        if "changelog" in command_lower and "release" not in command_lower:
            return await self._generate_changelog_only()

        # ── Determine bump type ───────────────────────────────────────────────
        bump_type = "patch"  # default
        if any(w in command_lower for w in ["major", "breaking"]):
            bump_type = "major"
        elif any(w in command_lower for w in ["minor", "feature", "feat"]):
            bump_type = "minor"
        elif any(w in command_lower for w in ["patch", "fix", "hotfix"]):
            bump_type = "patch"

        # ── Check for specific version ────────────────────────────────────────
        specific_version = self._extract_version(command)

        # ── Speak before starting ─────────────────────────────────────────────
        self.speak(release_started(specific_version or ""), blocking=False)

        # ── Run full release process ──────────────────────────────────────────
        return await self._create_release(bump_type, specific_version)

    async def _get_current_version(self) -> str:
        """Get the latest release version from GitHub."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.github.base_url}/repos/{self.github.org}/{self.github.repo}/releases/latest",
                    headers=self.github.headers,
                )
                if response.status_code == 404:
                    return "No releases found. This will be the first release."
                response.raise_for_status()
                release = response.json()
                return f"The latest version is {release['tag_name']}, released on {release['published_at'][:10]}."
        except Exception as e:
            logger.error("release.get_version_error", error=str(e))
            return "Could not retrieve the latest version from GitHub."

    async def _generate_changelog_only(self) -> str:
        """Generate changelog from recent commits."""
        try:
            commits = await self.github.get_latest_commits(count=10)
            if not commits:
                return no_changes_since_last_release()
            changelog = self._build_changelog(commits, "unreleased")
            return changelog_generated("unreleased", len(commits))
        except Exception as e:
            logger.error("release.changelog_error", error=str(e))
            return f"Could not generate changelog: {str(e)}"

    async def _create_release(
        self,
        bump_type: str,
        specific_version: str | None = None,
    ) -> str:
        """Full release — bump version, changelog, tag, GitHub release."""
        try:
            # Get latest commits
            commits = await self.github.get_latest_commits(count=20)
            if not commits:
                return no_changes_since_last_release()

            # Get current version
            current = await self._get_latest_tag()
            new_version = specific_version or self._bump_version(current, bump_type)
            tag = f"v{new_version}"

            # Build changelog
            changelog = self._build_changelog(commits, new_version)

            # Create GitHub release
            release = await self.github.create_release(
                tag=tag,
                name=f"Release {tag}",
                body=changelog,
                draft=False,
            )

            logger.info("release.created", version=new_version, tag=tag)
            return release_created(new_version, tag)

        except Exception as e:
            logger.error("release.create_error", error=str(e))
            return release_failed(specific_version or "unknown", str(e))

    async def _get_latest_tag(self) -> str:
        """Get the latest semver tag from GitHub."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.github.base_url}/repos/{self.github.org}/{self.github.repo}/tags",
                    headers=self.github.headers,
                )
                response.raise_for_status()
                tags = response.json()
                if not tags:
                    return "0.0.0"
                # Find latest semver tag
                for tag in tags:
                    name = tag["name"].lstrip("v")
                    if re.match(r"^\d+\.\d+\.\d+$", name):
                        return name
                return "0.0.0"
        except Exception as e:
            logger.error("release.get_tag_error", error=str(e))
            return "0.0.0"

    def _bump_version(self, current: str, bump_type: str) -> str:
        """Bump semver version string."""
        try:
            parts = [int(x) for x in current.split(".")]
            major, minor, patch = parts[0], parts[1], parts[2]
            if bump_type == "major":
                return f"{major + 1}.0.0"
            elif bump_type == "minor":
                return f"{major}.{minor + 1}.0"
            else:
                return f"{major}.{minor}.{patch + 1}"
        except Exception:
            return "0.1.0"

    def _build_changelog(self, commits: list, version: str) -> str:
        """Build a markdown changelog from commit list."""
        features  = []
        fixes     = []
        other     = []

        for commit in commits:
            msg = commit["message"]
            if msg.startswith("feat"):
                features.append(f"- {msg}")
            elif msg.startswith("fix"):
                fixes.append(f"- {msg}")
            else:
                other.append(f"- {msg}")

        lines = [f"## What's Changed in {version}\n"]
        if features:
            lines.append("### ✨ Features")
            lines.extend(features)
            lines.append("")
        if fixes:
            lines.append("### 🐛 Bug Fixes")
            lines.extend(fixes)
            lines.append("")
        if other:
            lines.append("### 🔧 Other Changes")
            lines.extend(other)

        return "\n".join(lines)

    @staticmethod
    def _extract_version(command: str) -> str | None:
        """Extract version number from command like 'tag version 2.5.0'."""
        match = re.search(r"\b(\d+\.\d+\.\d+)\b", command)
        return match.group(1) if match else None
