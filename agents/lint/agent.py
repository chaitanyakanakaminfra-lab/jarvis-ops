"""
agents/lint/agent.py
─────────────────────
Lint & Code Quality Agent — runs ruff, shellcheck, and ansible-lint.

Interview explanation:
  "The Lint agent is Jarvis's code quality enforcer. It listens for
   voice commands like 'run ruff on agents/' or 'shellcheck all scripts',
   runs the appropriate linter locally or triggers a GitHub Actions
   workflow_dispatch, and speaks the result back.

   It inherits from BaseAgent — logging, run history, timing, and error
   handling are all free. I only had to implement _run()."
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import httpx
import structlog

from agents.base_agent import BaseAgent
from agents.lint.voice_responses import (
    LintTool,
    lint_all_clean,
    lint_all_summary,
    lint_complete,
    lint_error,
    lint_no_issues,
    lint_running,
    lint_trigger_failed,
    lint_trigger_success,
    LINT_HELP,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"

_WORKFLOW_MAP = {
    LintTool.RUFF:         "pr-ruff.yaml",
    LintTool.SHELLCHECK:   "pr-shellcheck.yaml",
    LintTool.ANSIBLE_LINT: "pr-ansible-lint.yaml",
}


async def _gh_post(path: str, payload: dict, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{GITHUB_API}{path}", headers=headers, json=payload)
        r.raise_for_status()
        # 204 No Content on successful dispatch
        return r.json() if r.content else {}


async def _gh_get(path: str, token: str) -> dict | list:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{GITHUB_API}{path}", headers=headers)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Local lint runners
# ---------------------------------------------------------------------------

def _run_ruff(target: str) -> dict:
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format", "json", target],
            capture_output=True, text=True, timeout=60,
        )
        issues = json.loads(result.stdout) if result.stdout.strip() else []
        return {"tool": LintTool.RUFF, "exit_code": result.returncode,
                "issues": issues, "issue_count": len(issues)}
    except FileNotFoundError:
        return {"tool": LintTool.RUFF, "exit_code": -1, "issue_count": 0,
                "error": "ruff not installed — run: pip install ruff"}
    except subprocess.TimeoutExpired:
        return {"tool": LintTool.RUFF, "exit_code": -1, "issue_count": 0,
                "error": "ruff timed out after 60 seconds"}


def _run_shellcheck(target: str) -> dict:
    try:
        if target == ".":
            files = list(Path(".").rglob("*.sh"))
        else:
            files = [Path(target)]

        if not files:
            return {"tool": LintTool.SHELLCHECK, "exit_code": 0,
                    "issues": [], "issue_count": 0}

        result = subprocess.run(
            ["shellcheck", "--format=json"] + [str(f) for f in files],
            capture_output=True, text=True, timeout=60,
        )
        issues = json.loads(result.stdout) if result.stdout.strip() else []
        return {"tool": LintTool.SHELLCHECK, "exit_code": result.returncode,
                "issues": issues, "issue_count": len(issues)}
    except FileNotFoundError:
        return {"tool": LintTool.SHELLCHECK, "exit_code": -1, "issue_count": 0,
                "error": "shellcheck not installed — run: apt-get install shellcheck"}
    except subprocess.TimeoutExpired:
        return {"tool": LintTool.SHELLCHECK, "exit_code": -1, "issue_count": 0,
                "error": "shellcheck timed out after 60 seconds"}


def _run_ansible_lint(target: str) -> dict:
    try:
        result = subprocess.run(
            ["ansible-lint", "--format", "json", target],
            capture_output=True, text=True, timeout=120,
        )
        try:
            parsed = json.loads(result.stdout) if result.stdout.strip() else []
            issues = parsed if isinstance(parsed, list) else parsed.get("matches", [])
        except json.JSONDecodeError:
            issues = []
        return {"tool": LintTool.ANSIBLE_LINT, "exit_code": result.returncode,
                "issues": issues, "issue_count": len(issues)}
    except FileNotFoundError:
        return {"tool": LintTool.ANSIBLE_LINT, "exit_code": -1, "issue_count": 0,
                "error": "ansible-lint not installed — run: pip install ansible-lint"}
    except subprocess.TimeoutExpired:
        return {"tool": LintTool.ANSIBLE_LINT, "exit_code": -1, "issue_count": 0,
                "error": "ansible-lint timed out after 120 seconds"}


# ---------------------------------------------------------------------------
# Intent classifier
# ---------------------------------------------------------------------------

def _classify(command: str) -> dict:
    cmd = command.lower()

    # Tool
    tool = None
    if any(k in cmd for k in ("ruff", "python lint", "pep8")):
        tool = LintTool.RUFF
    elif any(k in cmd for k in ("shellcheck", "shell lint", "bash lint")):
        tool = LintTool.SHELLCHECK
    elif any(k in cmd for k in ("ansible", "playbook lint")):
        tool = LintTool.ANSIBLE_LINT

    # Target path
    target = "."
    for word in command.split():
        if "/" in word or word.endswith((".py", ".sh", ".yml", ".yaml")):
            target = word
            break

    # Action
    if any(k in cmd for k in ("trigger", "workflow", "github action", "ci lint")):
        return {"action": "trigger", "tool": tool, "target": target}
    if any(k in cmd for k in ("status", "last run", "latest")):
        return {"action": "status", "tool": tool, "target": target}
    if any(k in cmd for k in ("all linters", "lint everything", "run all", "full lint")):
        return {"action": "run_all", "tool": None, "target": target}
    if any(k in cmd for k in ("help", "what can you")):
        return {"action": "help", "tool": None, "target": target}
    if tool:
        return {"action": "run", "tool": tool, "target": target}

    return {"action": "unknown", "tool": None, "target": target}


# ---------------------------------------------------------------------------
# LintAgent
# ---------------------------------------------------------------------------

class LintAgent(BaseAgent):

    agent_id   = "lint"
    agent_name = "Lint & Code Quality Agent"

    def __init__(self):
        super().__init__()
        self._github_token = os.getenv("GITHUB_TOKEN", "")
        self._repo_owner   = os.getenv("GITHUB_REPO_OWNER", "chaitanyakanakaminfra-lab")
        self._repo_name    = os.getenv("GITHUB_REPO_NAME",  "jarvis-ops")

    async def _run(self, command: str) -> str:
        intent = _classify(command)
        action = intent["action"]
        tool   = intent["tool"]
        target = intent["target"]

        self._log.info("lint.intent", action=action, tool=tool, target=target)

        # ── run single linter locally ────────────────────────────────────
        if action == "run" and tool:
            self._log.info(lint_running(tool, target))

            runners = {
                LintTool.RUFF:         _run_ruff,
                LintTool.SHELLCHECK:   _run_shellcheck,
                LintTool.ANSIBLE_LINT: _run_ansible_lint,
            }
            result = await asyncio.to_thread(runners[tool], target)

            if "error" in result:
                return lint_error(tool, result["error"])
            if result["issue_count"] == 0:
                return lint_no_issues(tool, target)
            return lint_complete(tool, result["issue_count"], target)

        # ── run all linters ──────────────────────────────────────────────
        if action == "run_all":
            results = await asyncio.gather(
                asyncio.to_thread(_run_ruff,         target),
                asyncio.to_thread(_run_shellcheck,   target),
                asyncio.to_thread(_run_ansible_lint, target),
            )
            ruff_r, shell_r, ansible_r = results
            rc = ruff_r["issue_count"]
            sc = shell_r["issue_count"]
            ac = ansible_r["issue_count"]
            if rc == 0 and sc == 0 and ac == 0:
                return lint_all_clean()
            return lint_all_summary(rc, sc, ac)

        # ── trigger GitHub Actions ───────────────────────────────────────
        if action == "trigger":
            if not tool:
                return "Please specify which linter to trigger: ruff, shellcheck, or ansible-lint."
            if not self._github_token:
                return "GitHub token not configured. Set the GITHUB_TOKEN environment variable."

            workflow = _WORKFLOW_MAP[tool]
            try:
                await _gh_post(
                    f"/repos/{self._repo_owner}/{self._repo_name}"
                    f"/actions/workflows/{workflow}/dispatches",
                    {"ref": "main"},
                    self._github_token,
                )
                return lint_trigger_success(tool, workflow)
            except httpx.HTTPStatusError as exc:
                return lint_trigger_failed(tool, f"HTTP {exc.response.status_code}")
            except Exception as exc:
                return lint_trigger_failed(tool, str(exc))

        # ── workflow status ──────────────────────────────────────────────
        if action == "status":
            if not self._github_token:
                return "GitHub token not configured. Set the GITHUB_TOKEN environment variable."
            try:
                data = await _gh_get(
                    f"/repos/{self._repo_owner}/{self._repo_name}"
                    f"/actions/runs?per_page=5",
                    self._github_token,
                )
                runs = data.get("workflow_runs", [])
                if not runs:
                    return "No recent workflow runs found."
                run  = runs[0]
                conclusion = (run.get("conclusion") or run.get("status", "in_progress")).replace("_", " ")
                name = run.get("name", "workflow")
                return f"Latest GitHub Actions run: {name} — {conclusion}."
            except Exception as exc:
                return f"Could not fetch workflow status: {exc}"

        # ── help ─────────────────────────────────────────────────────────
        if action == "help":
            return LINT_HELP

        # ── unknown ──────────────────────────────────────────────────────
        return (
            "I didn't catch that lint command. "
            "Try: 'run ruff', 'shellcheck all scripts', "
            "'run all linters', or 'trigger ruff workflow'."
        )
