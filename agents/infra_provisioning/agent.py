from agents.base_agent import BaseAgent

class InfraProvisioningAgent(BaseAgent):
    agent_id   = "infra_provisioning"
    agent_name = "infra_provisioning Agent"

    async def _run(self, command: str) -> str:
        return f"InfraProvisioningAgent is not yet implemented. Coming in a future phase."
