"""
orchestrator/tools/slack_tool.py
──────────────────────────────────
Slack notifications for Jarvis agents.
"""

import httpx
import structlog
from config.settings import get_settings

logger = structlog.get_logger(__name__)


class SlackTool:

    def __init__(self):
        self.settings    = get_settings()
        self.webhook_url = getattr(self.settings, "slack_webhook_url", "")

    async def send_message(self, channel: str, message: str) -> bool:
        """Send a message to a Slack channel via webhook."""
        if not self.webhook_url:
            logger.warning("slack.no_webhook_configured")
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.webhook_url,
                    json={"channel": channel, "text": message},
                )
                response.raise_for_status()
                logger.info("slack.message_sent", channel=channel)
                return True
        except Exception as e:
            logger.error("slack.send_failed", error=str(e))
            return False

    async def send_alert(self, title: str, message: str, severity: str = "info") -> bool:
        """Send a formatted alert to Slack."""
        emoji = {"critical": "🚨", "high": "⚠️", "medium": "🔶", "info": "ℹ️"}.get(severity, "ℹ️")
        formatted = f"{emoji} *{title}*\n{message}"
        return await self.send_message("#alerts", formatted)
