from agents.base_agent import BaseAgent

class ComplianceAgent(BaseAgent):
    agent_id   = "compliance"
    agent_name = "compliance Agent"

    async def _run(self, command: str) -> str:
        return f"ComplianceAgent is not yet implemented. Coming in a future phase."
