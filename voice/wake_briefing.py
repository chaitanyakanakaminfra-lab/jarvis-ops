"""
voice/wake_briefing.py
───────────────────────
Wake phrase detector specifically for morning briefing.
Listens for "Jarvis wake up" and triggers the briefing.
"""

import asyncio
import struct
import threading
import structlog

logger = structlog.get_logger(__name__)


class BriefingWakeDetector:
    """
    Listens for "Jarvis wake up" and triggers morning briefing.
    Runs continuously in background.
    """

    def __init__(self, on_wake):
        self.on_wake    = on_wake
        self._running   = False
        self._thread    = None
        self._porcupine = None
        self._audio     = None
        self._stream    = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._listen_loop, daemon=True
        )
        self._thread.start()
        logger.info("wake_briefing.started")

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._audio:
            self._audio.terminate()
        if self._porcupine:
            self._porcupine.delete()
        logger.info("wake_briefing.stopped")

    def _listen_loop(self):
        try:
            import pvporcupine
            import pyaudio
            from config.settings import get_settings
            settings = get_settings()

            # Use "jarvis" keyword — responds to "Hey Jarvis" and "Jarvis"
            self._porcupine = pvporcupine.create(
                access_key=settings.porcupine_access_key,
                keywords=["jarvis"],
                sensitivities=[0.8],
            )

            self._audio  = pyaudio.PyAudio()
            self._stream = self._audio.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length,
            )

            logger.info(
                "wake_briefing.listening",
                phrase="Jarvis wake up",
            )

            while self._running:
                raw = self._stream.read(
                    self._porcupine.frame_length,
                    exception_on_overflow=False,
                )
                pcm = struct.unpack_from(
                    f"{self._porcupine.frame_length}h", raw
                )
                if self._porcupine.process(pcm) >= 0:
                    logger.info("wake_briefing.triggered")
                    threading.Thread(
                        target=self.on_wake, daemon=True
                    ).start()

        except Exception as e:
            logger.error("wake_briefing.error", error=str(e))
        finally:
            self.stop()
