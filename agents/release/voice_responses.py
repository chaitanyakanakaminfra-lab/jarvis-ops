"""
agents/release/voice_responses.py
───────────────────────────────────
Spoken responses for the Release & Versioning agent.
"""


def release_started(version: str = "") -> str:
    if version:
        return f"Starting release process for version {version}."
    return "Starting the release process now."


def release_created(version: str, tag: str = "") -> str:
    if tag:
        return f"Version {version} released successfully. Tag {tag} created on GitHub."
    return f"Version {version} released successfully on GitHub."


def release_failed(version: str, reason: str = "") -> str:
    if reason:
        return f"Release failed for version {version}. {reason}."
    return f"Release failed for version {version}. Check the logs."


def changelog_generated(version: str, commit_count: int) -> str:
    return f"Changelog generated for {version} from {commit_count} commits."


def tag_created(tag: str) -> str:
    return f"Git tag {tag} created and pushed to GitHub."


def tag_exists(tag: str) -> str:
    return f"Tag {tag} already exists. Please bump the version first."


def version_bumped(old: str, new: str, bump_type: str) -> str:
    return f"Version bumped from {old} to {new} — {bump_type} release."


def no_changes_since_last_release() -> str:
    return "No new commits since the last release. Nothing to release."


def draft_release_created(version: str) -> str:
    return f"Draft release for {version} created on GitHub. Review and publish when ready."
