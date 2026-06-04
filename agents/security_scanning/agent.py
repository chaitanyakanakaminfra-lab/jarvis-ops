import structlog
from agents.base_agent import BaseAgent
from orchestrator.tools.argo_tool import ArgoTool
from orchestrator.tools.github_tool import GitHubTool

logger = structlog.get_logger(__name__)


class SecurityScanningAgent(BaseAgent):
    agent_id   = "security_scanning"
    agent_name = "Security Scanning Agent"

    def __init__(self):
        super().__init__()
        self.argo   = ArgoTool()
        self.github = GitHubTool()

    async def _run(self, command: str) -> str:
        command_lower = command.lower()
        if any(w in command_lower for w in ["cve", "container", "image", "trivy"]):
            return await self._scan_images()
        if any(w in command_lower for w in ["secret", "leak", "credential"]):
            return await self._scan_secrets()
        if any(w in command_lower for w in ["sast", "code", "python", "bandit"]):
            return await self._scan_code()
        return await self._full_scan()

    async def _scan_images(self) -> str:
        try:
            result = await self.argo.submit_workflow(
                template_name="jarvis-trivy-scan",
                parameters={"image_name": "jarvis/orchestrator"},
                wait=False,
            )
            return f"Trivy CVE scan started for all Jarvis images. Workflow {result['workflow_name']} is running."
        except Exception as e:
            return f"CVE scan failed: {str(e)}"

    async def _scan_secrets(self) -> str:
        try:
            result = await self.argo.submit_workflow(
                template_name="jarvis-secret-scan",
                parameters={},
                wait=False,
            )
            return "Secret scanning started. Checking for leaked credentials, API keys, and tokens in the codebase."
        except Exception as e:
            return f"Secret scan failed: {str(e)}"

    async def _scan_code(self) -> str:
        try:
            result = await self.argo.submit_workflow(
                template_name="jarvis-bandit-scan",
                parameters={},
                wait=False,
            )
            return "Bandit SAST scan started. Analyzing Python code for security vulnerabilities."
        except Exception as e:
            return f"SAST scan failed: {str(e)}"

    async def _full_scan(self) -> str:
        try:
            await self.argo.submit_workflow(template_name="jarvis-trivy-scan", parameters={}, wait=False)
            return "Full security scan initiated — Trivy CVE scan, Bandit SAST, and secret detection all running."
        except Exception as e:
            return f"Security scan failed: {str(e)}"
