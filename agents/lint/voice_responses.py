"""
Jarvis — Lint & Code Quality Agent: Voice Responses
Day 9 | agents/lint/voice_responses.py

All TTS-ready strings for the lint agent.  Keep lines short and natural —
these are spoken aloud by Jarvis, not displayed in a UI.
"""

from enum import Enum


class LintTool(str, Enum):
    RUFF = "ruff"
    SHELLCHECK = "shellcheck"
    ANSIBLE_LINT = "ansible-lint"


# ---------------------------------------------------------------------------
# Running / in-progress
# ---------------------------------------------------------------------------


def lint_running(tool: LintTool, target: str) -> str:
    messages = {
        LintTool.RUFF: f"Running ruff on {target}. Checking Python code quality now.",
        LintTool.SHELLCHECK: f"Running shellcheck on {target}. Analyzing shell scripts.",
        LintTool.ANSIBLE_LINT: f"Running ansible-lint on {target}. Validating playbook rules.",
    }
    return messages.get(tool, f"Running {tool.value} on {target}.")


# ---------------------------------------------------------------------------
# Clean pass — zero issues
# ---------------------------------------------------------------------------


def lint_no_issues(tool: LintTool, target: str) -> str:
    messages = {
        LintTool.RUFF: f"Ruff found zero issues in {target}. Python code is clean.",
        LintTool.SHELLCHECK: f"Shellcheck found no problems in {target}. Shell scripts look solid.",
        LintTool.ANSIBLE_LINT: f"Ansible-lint passed with no violations in {target}. Playbooks are compliant.",
    }
    return messages.get(tool, f"{tool.value} passed. No issues found in {target}.")


# ---------------------------------------------------------------------------
# Issues found
# ---------------------------------------------------------------------------


def lint_complete(tool: LintTool, issue_count: int, target: str) -> str:
    noun = "issue" if issue_count == 1 else "issues"
    messages = {
        LintTool.RUFF: f"Ruff found {issue_count} {noun} in {target}. Check the output for details.",
        LintTool.SHELLCHECK: f"Shellcheck flagged {issue_count} {noun} in {target}. Review the shell scripts.",
        LintTool.ANSIBLE_LINT: f"Ansible-lint reported {issue_count} {noun} in {target}. Playbook review needed.",
    }
    return messages.get(
        tool,
        f"{tool.value} completed. {issue_count} {noun} found in {target}.",
    )


# ---------------------------------------------------------------------------
# Errors (tool missing, timeout, etc.)
# ---------------------------------------------------------------------------


def lint_error(tool: LintTool, error_detail: str) -> str:
    return (
        f"{tool.value} encountered an error: {error_detail}. "
        "Please check the agent logs for more information."
    )


# ---------------------------------------------------------------------------
# GitHub Actions workflow trigger
# ---------------------------------------------------------------------------


def lint_trigger_success(tool: LintTool | None, workflow_file: str) -> str:
    tool_name = tool.value if tool else "lint"
    return (
        f"GitHub Actions workflow {workflow_file} has been triggered for {tool_name}. "
        "Check the Actions tab for live progress."
    )


def lint_trigger_failed(tool: LintTool | None, error_detail: str) -> str:
    tool_name = tool.value if tool else "lint"
    return (
        f"Failed to trigger the {tool_name} workflow. "
        f"Error: {error_detail}. "
        "Verify your GitHub token and repository settings."
    )


# ---------------------------------------------------------------------------
# Status / informational
# ---------------------------------------------------------------------------

LINT_HELP = (
    "I can run three linters for you. "
    "Say 'run ruff' for Python, 'run shellcheck' for shell scripts, "
    "or 'run ansible-lint' for playbooks. "
    "You can also say 'run all linters' or 'trigger ruff workflow' "
    "to dispatch a GitHub Actions run."
)

LINT_NO_RUNS = (
    "No recent lint workflow runs were found in the repository."
)


def lint_status_summary(tool_name: str, conclusion: str) -> str:
    return (
        f"Latest {tool_name} run concluded with status: "
        f"{conclusion.replace('_', ' ')}."
    )


# ---------------------------------------------------------------------------
# Multi-tool summary (run all linters)
# ---------------------------------------------------------------------------


def lint_all_clean() -> str:
    return (
        "All three linters passed with zero violations. "
        "Ruff, shellcheck, and ansible-lint are all green."
    )


def lint_all_summary(ruff_count: int, shell_count: int, ansible_count: int) -> str:
    parts = []
    if ruff_count:
        parts.append(f"ruff: {ruff_count}")
    if shell_count:
        parts.append(f"shellcheck: {shell_count}")
    if ansible_count:
        parts.append(f"ansible-lint: {ansible_count}")

    total = ruff_count + shell_count + ansible_count
    summary = ", ".join(parts) if parts else "none"
    return (
        f"Full lint scan complete. Total violations: {total}. "
        f"Breakdown — {summary}."
    )
