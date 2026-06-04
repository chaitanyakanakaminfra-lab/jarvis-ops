"""
agents/cicd/agent.py
─────────────────────
CI/CD Pipeline Agent — triggers builds, tests, and deployments.

Interview explanation:
  "The CI/CD agent is the first real agent in Jarvis. It listens for
   voice commands like 'run the pipeline' or 'deploy to production',
   parses the intent using an LLM, maps it to the right Argo
   WorkflowTemplate, submits it, and speaks the result back.

   It inherits from BaseAgent — so logging, run history, and error
   handling are all free. I only had to implement _run()."
"""

import re
import structlog
from agents.base_agent import BaseAgent
from agents.cicd.voice_responses import (
    pipeline_started, pipeline_succeeded,
    pipeline_failed, deploy_started, deploy_succeeded,
    pipeline_status, no_pipeline_found,
)
from orchestrator.tools.argo_tool import ArgoTool
from orchestrator.tools.github_tool import GitHubTool

logger = structlog.get_logger(__name__)

# Map of intent keywords → WorkflowTemplate names
WORKFLOW_MAP = {
    "build":      "jarvis-build",
    "test":       "jarvis-build",
    "lint":       "jarvis-lint",
    "deploy":     "jarvis-deploy",
    "pipeline":   "jarvis-build",
    "ci":         "jarvis-build",
    "release":    "jarvis-deploy",
}


class CICDAgent(BaseAgent):

    agent_id   = "cicd_pipeline"
    agent_name = "CI/CD Pipeline Agent"

    def __init__(self):
        super().__init__()
        self.argo   = ArgoTool()
        self.github = GitHubTool()

    async def _run(self, command: str) -> str:
        """
        Parse the command and trigger the right workflow.

        Examples:
          "run the pipeline"           → submit jarvis-build
          "deploy to production"       → submit jarvis-deploy
          "check pipeline status"      → list recent workflows
          "run pipeline for PR 42"     → submit with pr_number=42
        """
        command_lower = command.lower()

        # ── Check status ──────────────────────────────────────────────────────
        if any(w in command_lower for w in ["status", "check", "what is"]):
            return await self._check_status()

        # ── Extract PR number if present ──────────────────────────────────────
        pr_number = self._extract_pr_number(command)

        # ── Map command to workflow template ──────────────────────────────────
        template_name = self._resolve_template(command_lower)

        if not template_name:
            return no_pipeline_found("unknown")

        # ── Build parameters ──────────────────────────────────────────────────
        parameters = {}
        if pr_number:
            parameters["pr_number"] = str(pr_number)

        # ── Speak before submitting (non-blocking) ────────────────────────────
        if "deploy" in command_lower:
            env = "production" if "prod" in command_lower else "staging"
            self.speak(deploy_started(env), blocking=False)
        else:
            self.speak(f"Starting {template_name} workflow now.", blocking=False)

        # ── Submit workflow ───────────────────────────────────────────────────
        try:
            result = await self.argo.submit_workflow(
                template_name=template_name,
                parameters=parameters,
                wait=False,    # don't block — speak result immediately
            )

            workflow_name = result["workflow_name"]
            logger.info("cicd.workflow_submitted", workflow=workflow_name)

            return pipeline_started(pr_number, workflow_name)

        except Exception as e:
            logger.error("cicd.submit_failed", error=str(e))
            return pipeline_failed(template_name, str(e))

    async def _check_status(self) -> str:
        """List recent workflows and speak their status."""
        try:
            workflows = await self.argo.list_workflows()
            if not workflows:
                return "No recent workflows found in the jarvis namespace."

            latest = workflows[0]
            return pipeline_status(latest["name"], latest["phase"])

        except Exception as e:
            return f"I could not retrieve workflow status: {str(e)}"

    def _resolve_template(self, command: str) -> str | None:
        """Map command keywords to a WorkflowTemplate name."""
        for keyword, template in WORKFLOW_MAP.items():
            if keyword in command:
                return template
        return None

    @staticmethod
    def _extract_pr_number(command: str) -> int | None:
        """Extract PR number from command like 'run pipeline for PR 42'."""
        match = re.search(r"\b(?:pr|pull request)\s*#?(\d+)", command, re.IGNORECASE)
        return int(match.group(1)) if match else None
