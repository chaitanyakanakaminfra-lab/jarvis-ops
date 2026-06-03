import asyncio
from enum import Enum, auto

import structlog

from config.settings import get_settings
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.wake_word import WakeWordDetector

logger = structlog.get_logger(__name__)


class SessionState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    ERROR = auto()


class VoiceSession:

    def __init__(self, brain_handler):
        self.settings = get_settings()
        self.brain_handler = brain_handler
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self._state = SessionState.IDLE
        self._wake_event = asyncio.Event()
        self._loop = None
        self._transcribed_text = ""

    async def run(self) -> None:
        self._loop = asyncio.get_event_loop()
        detector = WakeWordDetector(on_wake=self._on_wake_detected)
        detector.start()

        logger.info("voice_session.started")
        self.tts.play_sound("wake")
        self.tts.speak("Jarvis is online. Say Hey Jarvis to begin.", blocking=False)

        try:
            while True:
                await self._idle()
                await self._listen()
                await self._process()
                self._transition(SessionState.IDLE)
        except asyncio.CancelledError:
            logger.info("voice_session.cancelled")
        finally:
            detector.stop()

    async def _idle(self) -> None:
        self._transition(SessionState.IDLE)
        self._wake_event.clear()
        await self._wake_event.wait()

    async def _listen(self) -> None:
        self._transition(SessionState.LISTENING)
        self.tts.play_sound("wake")
        self._transcribed_text = await asyncio.get_event_loop().run_in_executor(
            None, self.stt.transcribe
        )
        logger.info("voice_session.transcribed", text=self._transcribed_text)
        if not self._transcribed_text.strip():
            self.tts.speak("I didn't catch that. Please try again.")
            self._transition(SessionState.IDLE)

    async def _process(self) -> None:
        if self._state == SessionState.IDLE:
            return
        self._transition(SessionState.PROCESSING)
        self.tts.play_sound("thinking")
        try:
            response = await self.brain_handler(self._transcribed_text)
            self._transition(SessionState.SPEAKING)
            self.tts.play_sound("done")
            self.tts.speak(response, blocking=True)
        except Exception as e:
            logger.error("voice_session.process_error", error=str(e))
            self._transition(SessionState.ERROR)
            self.tts.play_sound("error")
            self.tts.speak("I encountered an error. Please try again.")

    def _on_wake_detected(self) -> None:
        if self._state != SessionState.IDLE:
            return
        logger.info("voice_session.wake_detected")
        if self._loop:
            self._loop.call_soon_threadsafe(self._wake_event.set)

    def _transition(self, new_state: SessionState) -> None:
        old = self._state
        self._state = new_state
        if old != new_state:
            logger.info("voice_session.state_change", from_state=old.name, to_state=new_state.name)
