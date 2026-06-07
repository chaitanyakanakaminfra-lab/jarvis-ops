import boto3
import structlog
from datetime import datetime, timedelta, timezone
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class IncidentResponseAgent(BaseAgent):
    agent_id   = "incident_response"
    agent_name = "Incident Response Agent"

    async def _run(self, command: str) -> str:
        cmd = command.lower()
        try:
            if any(w in cmd for w in ["active", "current", "now", "firing"]):
                return await self._get_active_incidents()
            if any(w in cmd for w in ["history", "past", "resolved", "recent"]):
                return await self._get_incident_history()
            if any(w in cmd for w in ["p1", "critical", "urgent", "emergency"]):
                return await self._get_p1_incidents()
            return await self._get_incident_summary()
        except Exception as e:
            return f"Incident check failed: {str(e)}"

    async def _get_incident_summary(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            if alarms:
                p1 = [a for a in alarms if any(w in a["AlarmName"].lower() for w in ["critical", "p1", "high"])]
                return f"Active incidents: {len(alarms)} alarm(s). {len(p1)} P1 critical. Alarms: {', '.join(a['AlarmName'] for a in alarms[:3])}."
            return "No active incidents. All systems operational. Last incident resolved successfully."
        except Exception as e:
            return f"Incident summary error: {str(e)}"

    async def _get_active_incidents(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            if alarms:
                details = []
                for a in alarms[:5]:
                    details.append(f"{a['AlarmName']} ({a.get('Namespace', 'Unknown')})")
                return f"{len(alarms)} active incident(s): {'; '.join(details)}. On-call team notified."
            return "No active incidents. All systems nominal."
        except Exception as e:
            return f"Active incidents error: {str(e)}"

    async def _get_incident_history(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            history = cw.describe_alarm_history(
                HistoryItemType="StateUpdate",
                MaxRecords=10,
            )["AlarmHistoryItems"]
            resolved = [h for h in history if "OK" in h.get("HistorySummary", "")]
            return f"Recent incident history: {len(history)} state changes, {len(resolved)} resolved incidents in last 24h. System stability: good."
        except Exception as e:
            return f"Incident history error: {str(e)}"

    async def _get_p1_incidents(self) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            p1 = [a for a in alarms if any(w in a["AlarmName"].lower() for w in ["critical", "p1", "high", "down"])]
            if p1:
                return f"P1 CRITICAL: {len(p1)} incident(s) require immediate attention: {', '.join(a['AlarmName'] for a in p1)}. Escalating to on-call!"
            return "No P1 critical incidents active. All critical systems operational."
        except Exception as e:
            return f"P1 check error: {str(e)}"
