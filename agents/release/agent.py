from agents.base_agent import BaseAgent

class ReleaseAgent(BaseAgent):
    agent_id   = "release"
    agent_name = "release Agent"

    async def _run(self, command: str) -> str:
        return f"ReleaseAgent is not yet implemented. Coming in a future phase."
