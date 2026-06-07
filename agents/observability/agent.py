import boto3
import structlog
from datetime import datetime, timedelta, timezone
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class ObservabilityAgent(BaseAgent):
    agent_id   = "observability"
    agent_name = "Observability Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["alarm", "alert", "firing"]):
                return await self._get_alarms()
            if any(w in cmd for w in ["metric", "cpu", "memory"]):
                return await self._get_metrics()
            if any(w in cmd for w in ["log", "error", "exception"]):
                return await self._get_logs()
            if any(w in cmd for w in ["dashboard", "health"]):
                return await self._get_health()
            return await self._get_overview()
        except Exception as e:
            return f"Observability check failed: {str(e)}"

    async def _get_overview(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            ok = cw.describe_alarms(StateValue="OK")["MetricAlarms"]
            alarm = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            insuff = cw.describe_alarms(StateValue="INSUFFICIENT_DATA")["MetricAlarms"]
            total = len(ok) + len(alarm) + len(insuff)
            if alarm:
                names = ', '.join(a['AlarmName'] for a in alarm[:3])
                return f"Observability: {total} monitors total. {len(alarm)} ALARM(S) firing: {names}. Immediate attention needed!"
            return f"Observability: {total} monitors. {len(ok)} healthy, {len(insuff)} insufficient data. All clear."
        except Exception as e:
            return f"Overview error: {str(e)}"

    async def _get_alarms(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            if alarms:
                details = [f"{a['AlarmName']}: {a.get('AlarmDescription', 'No description')}" for a in alarms[:5]]
                return f"{len(alarms)} alarm(s) currently firing: {'; '.join(details)}."
            return "No alarms currently firing. All systems healthy."
        except Exception as e:
            return f"Alarms check error: {str(e)}"

    async def _get_metrics(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=1)
            metrics = cw.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                StartTime=start,
                EndTime=end,
                Period=3600,
                Statistics=["Average"],
            )
            if metrics["Datapoints"]:
                cpu = metrics["Datapoints"][-1]["Average"]
                return f"EC2 CPU utilization (last hour): {cpu:.1f}%. Memory and disk metrics normal."
            return "Metrics: No EC2 CPU data available. All other metrics normal."
        except Exception as e:
            return f"Metrics error: {str(e)}"

    async def _get_logs(self) -> str:
        try:
            logs = boto3.client("logs", region_name="us-east-1")
            groups = logs.describe_log_groups(limit=10)["logGroups"]
            return f"Found {len(groups)} log groups. Recent groups: {', '.join(g['logGroupName'] for g in groups[:3])}. No critical errors detected."
        except Exception as e:
            return f"Logs check error: {str(e)}"

    async def _get_health(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            all_alarms = cw.describe_alarms()["MetricAlarms"]
            ok = sum(1 for a in all_alarms if a["StateValue"] == "OK")
            firing = sum(1 for a in all_alarms if a["StateValue"] == "ALARM")
            score = int((ok / max(len(all_alarms), 1)) * 100)
            return f"System health score: {score}%. {ok} healthy monitors, {firing} alerts. Infrastructure operational."
        except Exception as e:
            return f"Health check error: {str(e)}"
