import structlog
from agents.base_agent import BaseAgent
from orchestrator.tools.argo_tool import ArgoTool
from orchestrator.tools.cloud_tool import CloudTool

logger = structlog.get_logger(__name__)


class InfraProvisioningAgent(BaseAgent):
    agent_id   = "infra_provisioning"
    agent_name = "Infra Provisioning Agent"

    def __init__(self):
        super().__init__()
        self.argo  = ArgoTool()
        self.cloud = CloudTool()

    async def _run(self, command: str) -> str:
        command_lower = command.lower()
        if any(w in command_lower for w in ["plan", "check", "show"]):
            return await self._terraform_plan()
        if any(w in command_lower for w in ["apply", "create", "provision"]):
            return await self._terraform_apply()
        if any(w in command_lower for w in ["destroy", "teardown", "delete"]):
            return "Terraform destroy requires manual confirmation for safety. Please run it directly."
        if any(w in command_lower for w in ["cluster", "eks"]):
            return await self._get_cluster_status()
        return await self._terraform_plan()

    async def _terraform_plan(self) -> str:
        try:
            result = await self.argo.submit_workflow(
                template_name="jarvis-terraform-plan",
                parameters={},
                wait=False,
            )
            return f"Terraform plan started. Workflow {result['workflow_name']} is running. I will report the changes."
        except Exception as e:
            return f"Terraform plan failed: {str(e)}"

    async def _terraform_apply(self) -> str:
        try:
            result = await self.argo.submit_workflow(
                template_name="jarvis-terraform-apply",
                parameters={},
                wait=False,
            )
            return f"Terraform apply started. Workflow {result['workflow_name']} is provisioning infrastructure."
        except Exception as e:
            return f"Terraform apply failed: {str(e)}"

    async def _get_cluster_status(self) -> str:
        try:
            info = await self.cloud.get_cluster_info()
            return f"EKS cluster {info['name']} is {info['status']} running Kubernetes {info['version']}."
        except Exception as e:
            return f"Could not get cluster status: {str(e)}"
