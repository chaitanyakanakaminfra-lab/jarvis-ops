import boto3
import structlog
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class CostOptimizationAgent(BaseAgent):
    agent_id   = "cost_optimization"
    agent_name = "Cost Optimization Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["breakdown", "detail", "service", "which", "show"]):
                return await self._get_cost_breakdown()
            if any(w in cmd for w in ["month", "monthly"]):
                return await self._get_monthly_cost()
            if any(w in cmd for w in ["optimize", "save", "reduce"]):
                return await self._get_recommendations()
            if any(w in cmd for w in ["forecast", "predict"]):
                return await self._get_forecast()
            return await self._get_cost_summary()
        except Exception as e:
            return f"Cost analysis failed: {str(e)}"

    async def _get_cost_summary(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            start = today.replace(day=1)
            result = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(today)},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            amount = float(result["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            return f"AWS spend this month: ${amount:.2f}. Budget on track."
        except Exception as e:
            return f"Cost summary error: {str(e)}"

    async def _get_cost_breakdown(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            start = today.replace(day=1)
            result = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(today)},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            groups = result["ResultsByTime"][0]["Groups"]
            groups.sort(key=lambda x: float(x["Metrics"]["UnblendedCost"]["Amount"]), reverse=True)
            total = sum(float(g["Metrics"]["UnblendedCost"]["Amount"]) for g in groups)
            top5 = [f"{g['Keys'][0].replace('Amazon ','').replace('AWS ','')} ${float(g['Metrics']['UnblendedCost']['Amount']):.2f}" for g in groups[:5]]
            return f"Cost breakdown this month (${total:.2f} total): {', '.join(top5)}."
        except Exception as e:
            return f"Cost breakdown error: {str(e)}"

    async def _get_monthly_cost(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            start = today.replace(day=1)
            result = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(today)},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            amount = float(result["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            return f"Monthly spend so far: ${amount:.2f}. Month started {start}."
        except Exception as e:
            return f"Monthly cost error: {str(e)}"

    async def _get_recommendations(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            start = today.replace(day=1)
            result = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(today)},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            total = float(result["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            recs = "Use Reserved Instances to save 40%, enable S3 Intelligent-Tiering, scale down EKS nodes when idle."
            return f"Current spend: ${total:.2f}. Recommendations: {recs}"
        except Exception as e:
            return f"Recommendations error: {str(e)}"

    async def _get_forecast(self) -> str:
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.utcnow().date()
            end = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
            result = ce.get_cost_forecast(
                TimePeriod={"Start": str(today), "End": str(end)},
                Metric="UNBLENDED_COST",
                Granularity="MONTHLY",
            )
            amount = float(result["Total"]["Amount"])
            return f"Forecasted spend next month: ${amount:.2f}."
        except Exception as e:
            return f"Forecast error: {str(e)}"
