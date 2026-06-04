from agents.base_agent import BaseAgent

class ReportingAgent(BaseAgent):
    agent_id   = "reporting"
    agent_name = "reporting Agent"

    async def _run(self, command: str) -> str:
        return f"ReportingAgent is not yet implemented. Coming in a future phase."
