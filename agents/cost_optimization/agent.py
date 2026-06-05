import boto3
from datetime import date
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class CostOptimizationAgent(BaseAgent):
    agent_id   = "cost_optimization"
    agent_name = "Cost Optimization Agent"

    async def _run(self, command: str) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = date.today()
            start = today.replace(day=1).strftime("%Y-%m-%d")
            end = today.strftime("%Y-%m-%d")
            
            response = ce.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            
            total = sum(
                float(g["Metrics"]["UnblendedCost"]["Amount"])
                for g in response["ResultsByTime"][0]["Groups"]
            )
            
            top_services = sorted(
                response["ResultsByTime"][0]["Groups"],
                key=lambda x: float(x["Metrics"]["UnblendedCost"]["Amount"]),
                reverse=True
            )[:3]
            
            top = ", ".join(
                f"{s['Keys'][0].split(' ')[1] if ' ' in s['Keys'][0] else s['Keys'][0]} ${float(s['Metrics']['UnblendedCost']['Amount']):.2f}"
                for s in top_services
            )
            
            return f"AWS spend this month is ${total:.2f}. Top services: {top}."
        except Exception as e:
            logger.error("cost.error", error=str(e))
            return f"Could not retrieve cost data: {str(e)}"
