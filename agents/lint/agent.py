"""
Jarvis — Lint & Code Quality Agent
Day 9 | agents/lint/agent.py

Handles voice commands routed from the FastAPI brain for lint/code-quality operations.
Supports ruff (Python), shellcheck (shell scripts), and ansible-lint (playbooks).
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter

from agents.lint.voice_responses import (
    LintTool,
    lint_complete,
    lint_error,
    lint_no_issues,
    lint_running,
    lint_trigger_failed,
    lint_trigger_success,
)

logger = logging.getLogger("jarvis.lint")

router = APIRouter(prefix="/agents/lint", tags=["lint"])

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GH_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

JARVIS_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "chaitanyakanakaminfra-lab")
JARVIS_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "jarvis-ops")


async def _gh_get(path: str) -> dict | list:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{GITHUB_API}{path}", headers=GH_HEADERS)
        r.raise_for_status()
        return r.json()


async def _gh_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{GITHUB_API}{path}", headers=GH_HEADERS, json=payload)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Local lint runners  (used when running directly on this machine)
# ---------------------------------------------------------------------------


def _run_ruff(target: str) -> dict[str, Any]:
    """Run ruff on *target* (file or directory). Returns structured result."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format", "json", target],
            capture_output=True,
            text=True,
            timeout=60,
        )
        import json

        issues = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "tool": LintTool.RUFF,
            "target": target,
            "exit_code": result.returncode,
            "issues": issues,
            "issue_count": len(issues),
            "stderr": result.stderr,
        }
    except FileNotFoundError:
        return {
            "tool": LintTool.RUFF,
            "target": target,
            "exit_code": -1,
            "issues": [],
            "issue_count": 0,
            "error": "ruff not installed — run: pip install ruff",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": LintTool.RUFF,
            "target": target,
            "exit_code": -1,
            "issues": [],
            "issue_count": 0,
            "error": "ruff timed out after 60 seconds",
        }


def _run_shellcheck(target: str) -> dict[str, Any]:
    """Run shellcheck on *target* (file or glob pattern)."""
    try:
        files = list(Path(".").rglob("*.sh")) if target == "." else [Path(target)]
        if not files:
            return {
                "tool": LintTool.SHELLCHECK,
                "target": target,
                "exit_code": 0,
                "issues": [],
                "issue_count": 0,
            }

        result = subprocess.run(
            ["shellcheck", "--format=json"] + [str(f) for f in files],
            capture_output=True,
            text=True,
            timeout=60,
        )
        import json

        issues = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "tool": LintTool.SHELLCHECK,
            "target": target,
            "exit_code": result.returncode,
            "issues": issues,
            "issue_count": len(issues),
            "stderr": result.stderr,
        }
    except FileNotFoundError:
        return {
            "tool": LintTool.SHELLCHECK,
            "target": target,
            "exit_code": -1,
            "issues": [],
            "issue_count": 0,
            "error": "shellcheck not installed — run: apt-get install shellcheck",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": LintTool.SHELLCHECK,
            "target": target,
            "exit_code": -1,
            "issues": [],
            "issue_count": 0,
            "error": "shellcheck timed out after 60 seconds",
        }


def _run_ansible_lint(target: str) -> dict[str, Any]:
    """Run ansible-lint on *target* (playbook file or directory)."""
    try:
        result = subprocess.run(
            ["ansible-lint", "--format", "json", target],
            capture_output=True,
            text=True,
            timeout=120,
        )
        import json

        # ansible-lint writes JSON to stdout when --format json is set
        try:
            parsed = json.loads(result.stdout) if result.stdout.strip() else []
            # ansible-lint >= 6 returns a list of MatchError dicts
            issues = parsed if isinstance(parsed, list) else parsed.get("matches", [])
        except json.JSONDecodeError:
            issues = []

        return {
            "tool": LintTool.ANSIBLE_LINT,
            "target": target,
            "exit_code": result.returncode,
            "issues": issues,
            "issue_count": len(issues),
            "stderr": result.stderr,
        }
    except FileNotFoundError:
        return {
            "tool": LintTool.ANSIBLE_LINT,
            "target": target,
            "exit_code": -1,
            "issues": [],
            "issue_count": 0,
            "error": "ansible-lint not installed — run: pip install ansible-lint",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": LintTool.ANSIBLE_LINT,
            "target": target,
            "exit_code": -1,
            "issues": [],
            "issue_count": 0,
            "error": "ansible-lint timed out after 120 seconds",
        }


# ---------------------------------------------------------------------------
# GitHub Actions workflow trigger
# ---------------------------------------------------------------------------


async def _trigger_workflow(
    workflow_file: str,
    ref: str = "main",
    inputs: dict | None = None,
) -> dict[str, Any]:
    """Dispatch a GitHub Actions workflow_dispatch event."""
    payload: dict[str, Any] = {"ref": ref}
    if inputs:
        payload["inputs"] = inputs

    try:
        await _gh_post(
            f"/repos/{JARVIS_REPO_OWNER}/{JARVIS_REPO_NAME}/actions/workflows/{workflow_file}/dispatches",
            payload,
        )
        return {"triggered": True, "workflow": workflow_file, "ref": ref}
    except httpx.HTTPStatusError as exc:
        return {
            "triggered": False,
            "workflow": workflow_file,
            "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
        }


# ---------------------------------------------------------------------------
# Intent router — maps voice command text → action
# ---------------------------------------------------------------------------


def _classify_intent(command: str) -> dict[str, Any]:
    """
    Simple keyword-based intent classifier.

    Returns:
        {
            "action": "run_local" | "trigger_workflow" | "status" | "unknown",
            "tool": LintTool | None,
            "target": str,
            "workflow_file": str | None,
        }
    """
    cmd = command.lower()

    # Determine tool
    tool: LintTool | None = None
    if any(k in cmd for k in ("ruff", "python lint", "pep8", "pyflakes")):
        tool = LintTool.RUFF
    elif any(k in cmd for k in ("shellcheck", "shell lint", "bash lint", "sh lint")):
        tool = LintTool.SHELLCHECK
    elif any(k in cmd for k in ("ansible", "playbook lint", "ansible-lint")):
        tool = LintTool.ANSIBLE_LINT

    # Determine target path (very naive — first path-looking token)
    words = command.split()
    target = "."
    for word in words:
        if "/" in word or word.endswith(".py") or word.endswith(".sh") or word.endswith(".yml"):
            target = word
            break

    # Determine action
    workflow_map = {
        LintTool.RUFF: "pr-ruff.yaml",
        LintTool.SHELLCHECK: "pr-shellcheck.yaml",
        LintTool.ANSIBLE_LINT: "pr-ansible-lint.yaml",
    }

    if any(k in cmd for k in ("trigger", "run workflow", "github action", "ci lint")):
        return {
            "action": "trigger_workflow",
            "tool": tool,
            "target": target,
            "workflow_file": workflow_map.get(tool) if tool else None,
        }

    if any(k in cmd for k in ("status", "last run", "latest lint", "check status")):
        return {"action": "status", "tool": tool, "target": target, "workflow_file": None}

    if tool is not None:
        return {
            "action": "run_local",
            "tool": tool,
            "target": target,
            "workflow_file": None,
        }

    # "lint everything" / "run all linters"
    if any(k in cmd for k in ("all linters", "lint everything", "full lint", "run all")):
        return {"action": "run_all", "tool": None, "target": target, "workflow_file": None}

    return {"action": "unknown", "tool": None, "target": target, "workflow_file": None}


# ---------------------------------------------------------------------------
# Main agent entry point (called by FastAPI brain)
# ---------------------------------------------------------------------------


async def handle_command(command: str) -> dict[str, Any]:
    """
    Process a voice command and return a structured response.

    Args:
        command: Raw voice command string from the brain router.

    Returns:
        {
            "voice_response": str,   # text for TTS
            "data": dict,            # structured result data
            "status": "ok" | "error",
        }
    """
    logger.info("Lint agent received command: %s", command)
    intent = _classify_intent(command)
    action = intent["action"]
    tool = intent["tool"]
    target = intent["target"]

    # --- run locally ---
    if action == "run_local" and tool is not None:
        voice_running = lint_running(tool, target)
        logger.info(voice_running)

        if tool == LintTool.RUFF:
            result = await asyncio.to_thread(_run_ruff, target)
        elif tool == LintTool.SHELLCHECK:
            result = await asyncio.to_thread(_run_shellcheck, target)
        elif tool == LintTool.ANSIBLE_LINT:
            result = await asyncio.to_thread(_run_ansible_lint, target)
        else:
            result = {"error": "Unknown tool", "issue_count": 0}

        if "error" in result:
            voice = lint_error(tool, result["error"])
            return {"voice_response": voice, "data": result, "status": "error"}

        if result["issue_count"] == 0:
            voice = lint_no_issues(tool, target)
        else:
            voice = lint_complete(tool, result["issue_count"], target)

        return {"voice_response": voice, "data": result, "status": "ok"}

    # --- run all linters ---
    if action == "run_all":
        results = {}
        for t, runner in [
            (LintTool.RUFF, _run_ruff),
            (LintTool.SHELLCHECK, _run_shellcheck),
            (LintTool.ANSIBLE_LINT, _run_ansible_lint),
        ]:
            results[t.value] = await asyncio.to_thread(runner, target)

        total = sum(r.get("issue_count", 0) for r in results.values())
        if total == 0:
            voice = "All linters passed with zero issues. Your code is clean, Chaitanya."
        else:
            summary = ", ".join(
                f"{r['issue_count']} {t}" for t, r in results.items() if r.get("issue_count", 0) > 0
            )
            voice = f"Lint complete. Found issues: {summary}. Total: {total} violations."

        return {"voice_response": voice, "data": results, "status": "ok"}

    # --- trigger GitHub Actions workflow ---
    if action == "trigger_workflow":
        if not intent["workflow_file"]:
            voice = "I'm not sure which workflow to trigger. Please specify ruff, shellcheck, or ansible-lint."
            return {"voice_response": voice, "data": {}, "status": "error"}

        result = await _trigger_workflow(intent["workflow_file"])
        if result["triggered"]:
            voice = lint_trigger_success(tool, intent["workflow_file"])
        else:
            voice = lint_trigger_failed(tool, result.get("error", "unknown error"))

        return {"voice_response": voice, "data": result, "status": "ok" if result["triggered"] else "error"}

    # --- status check ---
    if action == "status":
        try:
            runs = await _gh_get(
                f"/repos/{JARVIS_REPO_OWNER}/{JARVIS_REPO_NAME}/actions/runs?per_page=5"
            )
            recent = runs.get("workflow_runs", [])[:5]  # type: ignore[union-attr]
            if not recent:
                voice = "No recent workflow runs found in the repository."
            else:
                run = recent[0]
                conclusion = run.get("conclusion") or run.get("status", "in_progress")
                name = run.get("name", "workflow")
                voice = f"Latest GitHub Actions run: {name} — {conclusion.replace('_', ' ')}."
            return {"voice_response": voice, "data": {"runs": recent}, "status": "ok"}
        except Exception as exc:
            voice = f"Could not fetch workflow status: {exc}"
            return {"voice_response": voice, "data": {}, "status": "error"}

    # --- unknown ---
    voice = (
        "I didn't understand that lint command. "
        "Try: 'run ruff on agents', 'shellcheck all scripts', "
        "'trigger ansible lint workflow', or 'run all linters'."
    )
    return {"voice_response": voice, "data": {"intent": intent}, "status": "error"}


# ---------------------------------------------------------------------------
# FastAPI route (brain calls POST /agents/lint/command)
# ---------------------------------------------------------------------------


@router.post("/command")
async def lint_command_endpoint(body: dict):
    """
    POST /agents/lint/command
    Body: { "command": "<voice command string>" }
    """
    command = body.get("command", "")
    if not command:
        return {"voice_response": "No command received.", "data": {}, "status": "error"}
    return await handle_command(command)


@router.get("/health")
async def health():
    return {"agent": "lint", "status": "healthy"}
