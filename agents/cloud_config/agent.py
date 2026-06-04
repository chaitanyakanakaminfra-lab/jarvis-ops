from agents.base_agent import BaseAgent

class CloudConfigAgent(BaseAgent):
    agent_id   = "cloud_config"
    agent_name = "cloud_config Agent"

    async def _run(self, command: str) -> str:
        return f"CloudConfigAgent is not yet implemented. Coming in a future phase."
