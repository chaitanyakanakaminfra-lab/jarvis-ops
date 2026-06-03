import io
import math
import struct
import time
import wave
from enum import Enum

import pyaudio
import structlog

from config.settings import get_settings

logger = structlog.get_logger(__name__)

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2
CHUNK_SIZE = 1_024
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.5
MAX_RECORD_SECONDS = 15


class STTMode(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class SpeechToText:

    def __init__(self):
        self.settings = get_settings()
        self.mode = STTMode.LOCAL

    def transcribe(self) -> str:
        logger.info("stt.recording_start")
        audio_data = self._record_until_silence()
        if not audio_data:
            return ""
        if self.mode == STTMode.LOCAL:
            return self._transcribe_whisper(audio_data)
        return self._transcribe_deepgram(audio_data)

    def _record_until_silence(self) -> bytes | None:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        frames = []
        silent_chunks = 0
        max_silent = int(SAMPLE_RATE / CHUNK_SIZE * SILENCE_DURATION)
        max_total = int(SAMPLE_RATE / CHUNK_SIZE * MAX_RECORD_SECONDS)
        total = 0

        try:
            while total < max_total:
                chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                frames.append(chunk)
                total += 1
                if self._rms(chunk) < SILENCE_THRESHOLD:
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break
                else:
                    silent_chunks = 0
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

        return b"".join(frames) if frames else None

    @staticmethod
    def _rms(chunk: bytes) -> float:
        count = len(chunk) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"{count}h", chunk)
        return math.sqrt(sum(s * s for s in shorts) / count)

    def _transcribe_whisper(self, audio_bytes: bytes) -> str:
        try:
            import whisper
            import numpy as np
            if not hasattr(self, "_whisper_model"):
                self._whisper_model = whisper.load_model("base")
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            start = time.time()
            result = self._whisper_model.transcribe(audio_array, language="en", fp16=False)
            text = result["text"].strip()
            logger.info("stt.transcribed", text=text, duration_s=round(time.time() - start, 2))
            return text
        except Exception as e:
            logger.error("stt.whisper_error", error=str(e))
            return ""

    def _transcribe_deepgram(self, audio_bytes: bytes) -> str:
        try:
            from deepgram import DeepgramClient, PrerecordedOptions
            client = DeepgramClient(self.settings.deepgram_api_key)
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_bytes)
            response = client.listen.prerecorded.v("1").transcribe_file(
                {"buffer": wav_buffer.getvalue(), "mimetype": "audio/wav"},
                PrerecordedOptions(model="nova-2", language="en", smart_format=True),
            )
            text = response.results.channels[0].alternatives[0].transcript.strip()
            logger.info("stt.transcribed", text=text, mode="deepgram")
            return text
        except Exception as e:
            logger.error("stt.deepgram_error", error=str(e))
            return ""
