"""
voice/jarvis_voice.py
──────────────────────
Jarvis Voice Controller using OpenWakeWord + Deepgram + ElevenLabs.
Say "Hey Jarvis" → Jarvis listens → processes command → speaks back.
"""

import asyncio
import io
import os
import threading
import wave
import struct
import time
import httpx
import numpy as np
import pyaudio
from openwakeword.model import Model

JARVIS_API = "http://localhost:8000"
CHUNK      = 1280
FORMAT     = pyaudio.paInt16
CHANNELS   = 1
RATE       = 16000
SILENCE_THRESHOLD = 500
SILENCE_SECONDS   = 1.5


def rms(data):
    count  = len(data) // 2
    shorts = struct.unpack(f"{count}h", data)
    return (sum(s * s for s in shorts) / count) ** 0.5


def speak(text: str) -> None:
    """Speak text using ElevenLabs TTS."""
    api_key  = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

    if not api_key or api_key == "dummy":
        print(f"[JARVIS]: {text}")
        return

    try:
        import requests
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                },
            },
            stream=True,
        )
        if response.status_code == 200:
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=22050,
                output=True,
            )
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    stream.write(chunk)
            stream.stop_stream()
            stream.close()
            audio.terminate()
        else:
            print(f"[JARVIS]: {text}")
    except Exception as e:
        print(f"[JARVIS]: {text}")
        print(f"TTS error: {e}")


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe audio using Deepgram."""
    api_key = os.getenv("DEEPGRAM_API_KEY", "")

    if not api_key or api_key == "...":
        return input("(no mic/STT) Type command: ")

    try:
        import requests

        # Wrap in WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(audio_bytes)

        response = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&language=en",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/wav",
            },
            data=buf.getvalue(),
            timeout=30,
        )
        result = response.json()
        text   = result["results"]["channels"][0]["alternatives"][0]["transcript"]
        print(f"[YOU]: {text}")
        return text.strip()
    except Exception as e:
        print(f"STT error: {e}")
        return ""


def record_until_silence() -> bytes:
    """Record from mic until silence detected."""
    audio  = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT, channels=CHANNELS,
        rate=RATE, input=True,
        frames_per_buffer=CHUNK,
    )
    frames         = []
    silent_chunks  = 0
    max_silent     = int(RATE / CHUNK * SILENCE_SECONDS)
    max_total      = int(RATE / CHUNK * 15)
    total          = 0

    print("[JARVIS]: Listening...")

    while total < max_total:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        total += 1
        if rms(data) < SILENCE_THRESHOLD:
            silent_chunks += 1
            if silent_chunks >= max_silent:
                break
        else:
            silent_chunks = 0

    stream.stop_stream()
    stream.close()
    audio.terminate()
    return b"".join(frames)


async def ask_jarvis(command: str) -> str:
    """Send command to Jarvis API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{JARVIS_API}/agents/run",
                json={"command": command},
            )
            return response.json().get("response", "I could not process that.")
    except Exception as e:
        return f"Could not reach Jarvis API: {e}"


async def run_voice_session():
    """Main voice loop."""
    print("\n" + "="*50)
    print("  JARVIS VOICE CONTROL")
    print("  Say 'Hey Jarvis' to activate")
    print("="*50 + "\n")

    # Load OpenWakeWord model
    print("[SYSTEM]: Loading wake word model...")
    oww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    print("[SYSTEM]: Wake word model loaded. Say 'Hey Jarvis'...\n")

    speak("Jarvis voice control active. Say Hey Jarvis to begin.")

    audio  = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT, channels=CHANNELS,
        rate=RATE, input=True,
        frames_per_buffer=CHUNK,
    )

    try:
        while True:
            # Listen for wake word
            data = stream.read(CHUNK, exception_on_overflow=False)
            pcm  = np.frombuffer(data, dtype=np.int16)
            prediction = oww.predict(pcm)

            # Check if wake word detected
            scores = list(oww.prediction_buffer["hey_jarvis_v0.1"])
            if scores and scores[-1] > 0.5:
                print("\n[SYSTEM]: Wake word detected!")
                speak("Yes?")

                # Stop wake word stream
                stream.stop_stream()
                stream.close()

                # Record command
                audio_data = record_until_silence()

                # Transcribe
                command = transcribe(audio_data)

                if command:
                    print(f"[PROCESSING]: {command}")
                    speak("Let me check that for you.")

                    # Get response from Jarvis
                    response = await ask_jarvis(command)
                    print(f"[JARVIS]: {response}")
                    speak(response)

                # Restart wake word listening
                stream = audio.open(
                    format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK,
                )
                print("\n[SYSTEM]: Listening for wake word...\n")

    except KeyboardInterrupt:
        print("\n[SYSTEM]: Voice control stopped.")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()


if __name__ == "__main__":
    # Load env
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_voice_session())
