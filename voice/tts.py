import subprocess
import platform
import threading
from pathlib import Path

import structlog

from config.settings import get_settings

logger = structlog.get_logger(__name__)

SOUNDS_DIR = Path(__file__).parent / "sounds"


class TextToSpeech:

    def __init__(self):
        self.settings = get_settings()
        self._lock = threading.Lock()

    def speak(self, text: str, blocking: bool = True) -> None:
        if not text.strip():
            return
        logger.info("tts.speak", text=text[:80])
        if blocking:
            self._speak_sync(text)
        else:
            threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()

    def _speak_sync(self, text: str) -> None:
        with self._lock:
            try:
                self._speak_elevenlabs(text)
            except Exception as e:
                logger.error("tts.error", error=str(e))
                print(f"[JARVIS]: {text}")

    def _speak_elevenlabs(self, text: str) -> None:
        from elevenlabs import ElevenLabs, VoiceSettings
        import pyaudio

        client = ElevenLabs(api_key=self.settings.elevenlabs_api_key)
        audio_stream = client.generate(
            text=text,
            voice=self.settings.elevenlabs_voice_id,
            model="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.2,
                use_speaker_boost=True,
            ),
            stream=True,
        )

        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=22050, output=True)
        try:
            for chunk in audio_stream:
                if chunk:
                    stream.write(chunk)
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def play_sound(self, sound_name: str) -> None:
        sound_file = SOUNDS_DIR / f"{sound_name}.mp3"
        if not sound_file.exists():
            return
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["afplay", str(sound_file)])
            elif platform.system() == "Windows":
                subprocess.Popen(["powershell", "-c", f"(New-Object Media.SoundPlayer '{sound_file}').PlaySync()"])
            else:
                subprocess.Popen(["mpg123", "-q", str(sound_file)])
        except Exception as e:
            logger.debug("tts.sound_error", sound=sound_name, error=str(e))
