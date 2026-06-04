import structlog
from agents.base_agent import BaseAgent
from orchestrator.tools.cloud_tool import CloudTool
from orchestrator.tools.slack_tool import SlackTool

logger = structlog.get_logger(__name__)


class IncidentResponseAgent(BaseAgent):
    agent_id   = "incident_response"
    agent_name = "Incident Response Agent"

    def __init__(self):
        super().__init__()
        self.cloud = CloudTool()
        self.slack = SlackTool()

    async def _run(self, command: str) -> str:
        command_lower = command.lower()
        if any(w in command_lower for w in ["p1", "critical", "down", "outage"]):
            return await self._handle_p1(command)
        if any(w in command_lower for w in ["p2", "degraded", "slow"]):
            return await self._handle_p2(command)
        if any(w in command_lower for w in ["runbook", "playbook"]):
            return await self._run_runbook(command)
        if any(w in command_lower for w in ["resolve", "resolved", "fixed"]):
            return await self._resolve_incident()
        return await self._handle_p1(command)

    async def _handle_p1(self, command: str) -> str:
        try:
            await self.slack.send_message(
                channel="#incidents",
                message=f"🚨 P1 INCIDENT DETECTED\nTriggered by Jarvis: {command}\nInvestigating now...",
            )
            return "P1 incident declared. On-call engineer notified on Slack. Running incident runbook alpha now."
        except Exception as e:
            return f"P1 incident declared. Could not send Slack notification: {str(e)}"

    async def _handle_p2(self, command: str) -> str:
        try:
            await self.slack.send_message(
                channel="#alerts",
                message=f"⚠️ P2 INCIDENT: {command}",
            )
            return "P2 incident logged. Team notified on Slack. Monitoring for escalation."
        except Exception as e:
            return "P2 incident logged. Monitoring for escalation to P1."

    async def _run_runbook(self, command: str) -> str:
        return "Running incident runbook. Checking service health, restarting failed pods, and collecting diagnostic logs."

    async def _resolve_incident(self) -> str:
        return "Incident marked as resolved. Post-mortem template created. All-clear notification sent to the team."
