import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import structlog

from config.settings import get_settings


class AgentStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    SKIPPED = "skipped"


@dataclass
class AgentRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_name: str = ""
    command: str = ""
    status: AgentStatus = AgentStatus.RUNNING
    result: str = ""
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):

    agent_id: str = ""
    agent_name: str = ""

    def __init__(self):
        self.settings = get_settings()
        self._log = structlog.get_logger(self.__class__.__name__)
        self._tts = None

    async def execute(self, command: str) -> str:
        run = AgentRun(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            command=command,
        )
        self._log.info("agent.started", agent=self.agent_id, run_id=run.run_id, command=command)
        start = time.monotonic()

        try:
            result = await self._run(command)
            run.status = AgentStatus.SUCCESS
            run.result = result
            run.duration_ms = int((time.monotonic() - start) * 1000)
            self._log.info("agent.succeeded", agent=self.agent_id, duration_ms=run.duration_ms)
            await self._save_run(run)
            return result

        except Exception as e:
            run.status = AgentStatus.FAILURE
            run.error = str(e)
            run.duration_ms = int((time.monotonic() - start) * 1000)
            self._log.error("agent.failed", agent=self.agent_id, error=str(e))
            await self._save_run(run)
            return f"I encountered an issue with {self.agent_name}: {str(e)}"

        finally:
            run.finished_at = datetime.now(timezone.utc)

    @abstractmethod
    async def _run(self, command: str) -> str:
        ...

    def speak(self, text: str, blocking: bool = False) -> None:
        if not self.settings.jarvis_voice_enabled:
            return
        if self._tts is None:
            from voice.tts import TextToSpeech
            self._tts = TextToSpeech()
        self._tts.speak(text, blocking=blocking)

    async def _save_run(self, run: AgentRun) -> None:
        try:
            from memory.run_history import RunHistory
            await RunHistory.save(run)
        except Exception as e:
            self._log.warning("agent.run_save_failed", error=str(e))

    def _format_duration(self, ms: int) -> str:
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60_000:
            return f"{ms / 1000:.1f}s"
        return f"{ms / 60_000:.1f}m"
