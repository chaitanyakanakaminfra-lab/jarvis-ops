from agents.base_agent import BaseAgent

class SecurityScanningAgent(BaseAgent):
    agent_id   = "security_scanning"
    agent_name = "security_scanning Agent"

    async def _run(self, command: str) -> str:
        return f"SecurityScanningAgent is not yet implemented. Coming in a future phase."
