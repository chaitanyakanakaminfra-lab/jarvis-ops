import struct
import threading
from collections.abc import Callable

import pvporcupine
import pyaudio
import structlog

from config.settings import get_settings

logger = structlog.get_logger(__name__)


class WakeWordDetector:

    def __init__(self, on_wake: Callable[[], None]):
        self.settings = get_settings()
        self.on_wake = on_wake
        self._porcupine = None
        self._audio = None
        self._stream = None
        self._thread = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("wake_word.started", keyword=self.settings.jarvis_wake_word)

    def stop(self) -> None:
        self._running = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._audio:
            self._audio.terminate()
        if self._porcupine:
            self._porcupine.delete()
        logger.info("wake_word.stopped")

    def _listen_loop(self) -> None:
        try:
            self._porcupine = pvporcupine.create(
                access_key=self.settings.porcupine_access_key,
                keywords=[self.settings.jarvis_wake_word],
                sensitivities=[0.7],
            )
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length,
            )
            logger.info("wake_word.listening")

            while self._running:
                raw_pcm = self._stream.read(
                    self._porcupine.frame_length,
                    exception_on_overflow=False,
                )
                pcm_frame = struct.unpack_from(f"{self._porcupine.frame_length}h", raw_pcm)
                keyword_index = self._porcupine.process(pcm_frame)
                if keyword_index >= 0:
                    logger.info("wake_word.detected")
                    threading.Thread(target=self.on_wake, daemon=True).start()

        except Exception as e:
            logger.error("wake_word.error", error=str(e))
        finally:
            self.stop()
