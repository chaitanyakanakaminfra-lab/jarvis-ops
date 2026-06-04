from agents.base_agent import BaseAgent

class ObservabilityAgent(BaseAgent):
    agent_id   = "observability"
    agent_name = "observability Agent"

    async def _run(self, command: str) -> str:
        return f"ObservabilityAgent is not yet implemented. Coming in a future phase."
