from agents.base_agent import BaseAgent

class IncidentResponseAgent(BaseAgent):
    agent_id   = "incident_response"
    agent_name = "incident_response Agent"

    async def _run(self, command: str) -> str:
        return f"IncidentResponseAgent is not yet implemented. Coming in a future phase."
