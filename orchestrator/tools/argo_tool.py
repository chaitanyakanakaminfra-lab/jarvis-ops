"""
orchestrator/tools/argo_tool.py
────────────────────────────────
LangChain tool for submitting and monitoring Argo Workflows.

Interview explanation:
  "The Argo tool wraps the Argo Workflows API. Instead of running kubectl
   commands, I use the Argo Server REST API — this works from any pod
   or service without needing kubectl installed. I submit a WorkflowTemplate
   by name, poll for completion, and return the result as a string that
   Jarvis speaks back to the user."
"""

import httpx
import structlog
from config.settings import get_settings

logger = structlog.get_logger(__name__)


class ArgoTool:

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.argo_server_url
        self.namespace = self.settings.argo_namespace
        self.headers = {
            "Authorization": f"Bearer {self.settings.argo_token}",
            "Content-Type": "application/json",
        }

    async def submit_workflow(
        self,
        template_name: str,
        parameters: dict | None = None,
        wait: bool = False,
    ) -> dict:
        """
        Submit an Argo WorkflowTemplate and return the workflow name.

        Args:
            template_name: Name of the WorkflowTemplate to submit
            parameters:    Key-value pairs passed to the workflow
            wait:          If True, poll until workflow completes
        Returns:
            dict with workflow name, status, and metadata
        """
        payload = {
            "resourceKind": "WorkflowTemplate",
            "resourceName": template_name,
            "submitOptions": {
                "parameters": [
                    f"{k}={v}" for k, v in (parameters or {}).items()
                ]
            },
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/workflows/{self.namespace}/submit",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                workflow = response.json()
                workflow_name = workflow["metadata"]["name"]

                logger.info(
                    "argo.workflow_submitted",
                    template=template_name,
                    workflow=workflow_name,
                )

                if wait:
                    return await self.wait_for_completion(workflow_name)

                return {
                    "workflow_name": workflow_name,
                    "status": "submitted",
                    "template": template_name,
                }

        except httpx.HTTPStatusError as e:
            logger.error("argo.submit_error", error=str(e), template=template_name)
            raise RuntimeError(f"Failed to submit workflow {template_name}: {e.response.text}")

    async def get_workflow_status(self, workflow_name: str) -> dict:
        """Get current status of a workflow."""
        try:
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/workflows/{self.namespace}/{workflow_name}",
                    headers=self.headers,
                )
                response.raise_for_status()
                workflow = response.json()
                phase = workflow.get("status", {}).get("phase", "Unknown")
                return {
                    "workflow_name": workflow_name,
                    "phase": phase,
                    "finished": phase in ["Succeeded", "Failed", "Error"],
                }
        except Exception as e:
            logger.error("argo.status_error", error=str(e))
            return {"workflow_name": workflow_name, "phase": "Unknown", "finished": False}

    async def wait_for_completion(
        self, workflow_name: str, timeout_seconds: int = 300
    ) -> dict:
        """Poll workflow until it completes or times out."""
        import asyncio
        elapsed = 0
        poll_interval = 5

        while elapsed < timeout_seconds:
            status = await self.get_workflow_status(workflow_name)
            if status["finished"]:
                logger.info(
                    "argo.workflow_finished",
                    workflow=workflow_name,
                    phase=status["phase"],
                )
                return status
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return {
            "workflow_name": workflow_name,
            "phase": "Timeout",
            "finished": False,
        }

    async def list_workflows(self, label_selector: str = "") -> list:
        """List recent workflows in the jarvis namespace."""
        try:
            params = {"listOptions.limit": 10}
            if label_selector:
                params["listOptions.labelSelector"] = label_selector

            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/workflows/{self.namespace}",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                items = response.json().get("items", []) or []
                return [
                    {
                        "name": w["metadata"]["name"],
                        "phase": w.get("status", {}).get("phase", "Unknown"),
                        "started": w.get("status", {}).get("startedAt", ""),
                    }
                    for w in items
                ]
        except Exception as e:
            logger.error("argo.list_error", error=str(e))
            return []
