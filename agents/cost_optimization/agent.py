from agents.base_agent import BaseAgent

class CostOptimizationAgent(BaseAgent):
    agent_id   = "cost_optimization"
    agent_name = "cost_optimization Agent"

    async def _run(self, command: str) -> str:
        return f"CostOptimizationAgent is not yet implemented. Coming in a future phase."
