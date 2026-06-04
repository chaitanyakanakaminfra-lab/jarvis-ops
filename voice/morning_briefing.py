"""
voice/morning_briefing.py
──────────────────────────
JARVIS Morning Briefing System.

When triggered by "Jarvis wake up", queries all 15 agents
and delivers a spoken status briefing one by one —
exactly like Tony Stark's JARVIS morning briefing.
"""

import asyncio
from datetime import datetime
import httpx
import structlog

logger = structlog.get_logger(__name__)

JARVIS_API = "http://localhost:8000"

# Morning briefing script — each agent gets a status check
BRIEFING_AGENTS = [
    {
        "name": "CI/CD Pipeline",
        "command": "pipeline status overnight",
        "intro": "CI/CD Pipeline status.",
    },
    {
        "name": "Infrastructure",
        "command": "check the cluster health",
        "intro": "Infrastructure and Kubernetes.",
    },
    {
        "name": "Cloud Costs",
        "command": "how are cloud costs",
        "intro": "Cloud spend update.",
    },
    {
        "name": "Security",
        "command": "scan for vulnerabilities",
        "intro": "Security scan results.",
    },
    {
        "name": "Compliance",
        "command": "run compliance check",
        "intro": "Compliance status.",
    },
    {
        "name": "Observability",
        "command": "hows the system",
        "intro": "System health overview.",
    },
    {
        "name": "Incidents",
        "command": "any active incidents",
        "intro": "Incident status.",
    },
    {
        "name": "Weekly Report",
        "command": "weekly summary",
        "intro": "Performance summary.",
    },
]


class MorningBriefing:
    """
    Delivers the JARVIS morning briefing.
    Queries all agents and speaks results one by one.
    """

    def __init__(self):
        self._tts = None

    def _get_tts(self):
        if not self._tts:
            from voice.tts import TextToSpeech
            self._tts = TextToSpeech()
        return self._tts

    def speak(self, text: str) -> None:
        """Speak text using ElevenLabs TTS."""
        try:
            tts = self._get_tts()
            tts.speak(text, blocking=True)
        except Exception as e:
            logger.error("briefing.speak_error", error=str(e))
            print(f"[JARVIS]: {text}")

    async def query_agent(self, command: str) -> str:
        """Query Jarvis API for agent status."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{JARVIS_API}/agents/run",
                    json={"command": command},
                )
                response.raise_for_status()
                return response.json().get("response", "Status unavailable.")
        except Exception as e:
            logger.error("briefing.query_error", error=str(e))
            return "Status unavailable at this time."

    async def run(self, websocket_callback=None) -> None:
        """
        Run the full morning briefing.
        websocket_callback: optional function to send updates to UI
        """
        now = datetime.now()
        hour = now.hour
        greeting = (
            "Good morning" if 5 <= hour < 12
            else "Good afternoon" if 12 <= hour < 17
            else "Good evening"
        )

        # Opening greeting
        opening = (
            f"{greeting} Chaitanya. All systems online. "
            f"Running your morning briefing. "
            f"Today is {now.strftime('%A, %B %d')}. "
            f"Checking all {len(BRIEFING_AGENTS)} systems now."
        )
        self.speak(opening)

        if websocket_callback:
            await websocket_callback({
                "type": "briefing_start",
                "message": opening,
                "total_agents": len(BRIEFING_AGENTS),
            })

        # Brief each agent one by one
        results = []
        for i, agent in enumerate(BRIEFING_AGENTS):
            logger.info("briefing.checking_agent", agent=agent["name"])

            # Notify UI — currently checking this agent
            if websocket_callback:
                await websocket_callback({
                    "type": "agent_checking",
                    "agent": agent["name"],
                    "index": i,
                })

            # Get agent status
            status = await self.query_agent(agent["command"])

            # Speak intro + status
            spoken = f"{agent['intro']} {status}"
            self.speak(spoken)

            # Small pause between agents — feels natural
            await asyncio.sleep(0.5)

            result = {
                "agent": agent["name"],
                "status": status,
                "spoken": spoken,
            }
            results.append(result)

            # Notify UI — agent done
            if websocket_callback:
                await websocket_callback({
                    "type": "agent_done",
                    "agent": agent["name"],
                    "status": status,
                    "index": i,
                })

        # Closing statement
        closing = (
            "Morning briefing complete. "
            "All systems have been checked. "
            "I am ready for your commands, Chaitanya."
        )
        self.speak(closing)

        if websocket_callback:
            await websocket_callback({
                "type": "briefing_complete",
                "message": closing,
                "results": results,
            })

        logger.info("briefing.complete", agents_checked=len(results))
        return results


async def run_briefing():
    """Standalone function to run morning briefing."""
    briefing = MorningBriefing()
    results = await briefing.run()
    return results


if __name__ == "__main__":
    asyncio.run(run_briefing())
