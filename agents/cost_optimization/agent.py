import structlog
from agents.base_agent import BaseAgent
from orchestrator.tools.cloud_tool import CloudTool

logger = structlog.get_logger(__name__)


class CostOptimizationAgent(BaseAgent):
    agent_id   = "cost_optimization"
    agent_name = "Cost Optimization Agent"

    def __init__(self):
        super().__init__()
        self.cloud = CloudTool()

    async def _run(self, command: str) -> str:
        command_lower = command.lower()
        if any(w in command_lower for w in ["spend", "cost", "bill", "how much"]):
            return await self._get_spend()
        if any(w in command_lower for w in ["saving", "optimize", "reduce", "rightsize"]):
            return await self._get_savings()
        if any(w in command_lower for w in ["service", "breakdown", "detail"]):
            return await self._cost_by_service()
        return await self._get_spend()

    async def _get_spend(self) -> str:
        try:
            cost = await self.cloud.get_monthly_cost()
            amount = cost.get("amount", 0)
            return f"Your AWS spend this month is ${amount:.2f}. The billing period covers {cost.get('period', 'this month')}."
        except Exception as e:
            return f"Could not retrieve AWS costs: {str(e)}"

    async def _get_savings(self) -> str:
        try:
            services = await self.cloud.get_cost_by_service()
            if not services:
                return "No cost data available. Make sure AWS Cost Explorer is enabled."
            top = services[0]
            return (
                f"Biggest cost driver is {top['service']} at ${top['cost']:.2f} this month. "
                f"I recommend reviewing idle resources and rightsizing instances to reduce spend."
            )
        except Exception as e:
            return f"Could not calculate savings: {str(e)}"

    async def _cost_by_service(self) -> str:
        try:
            services = await self.cloud.get_cost_by_service()
            if not services:
                return "No cost breakdown available."
            top3 = services[:3]
            summary = ", ".join(f"{s['service']} ${s['cost']:.2f}" for s in top3)
            return f"Top AWS services by cost this month: {summary}."
        except Exception as e:
            return f"Could not get cost breakdown: {str(e)}"
