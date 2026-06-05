import boto3
import structlog
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

class ObservabilityAgent(BaseAgent):
    agent_id   = "observability"
    agent_name = "Observability Agent"

    async def _run(self, command: str) -> str:
        try:
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            
            # Get active alarms
            alarms = cw.describe_alarms(StateValue="ALARM")["MetricAlarms"]
            ok_alarms = cw.describe_alarms(StateValue="OK")["MetricAlarms"]
            
            if alarms:
                names = ", ".join(a["AlarmName"] for a in alarms[:3])
                return f"{len(alarms)} active CloudWatch alarm(s): {names}. Immediate attention required."
            
            return f"All CloudWatch metrics normal. {len(ok_alarms)} alarms in OK state. No issues detected."
        except Exception as e:
            logger.error("observability.error", error=str(e))
            return f"Could not reach CloudWatch: {str(e)}"
