"""
Browser-based voice server.
Receives audio from browser via WebSocket,
transcribes with Deepgram, processes with Jarvis,
returns ElevenLabs audio back to browser.
"""
import asyncio
import base64
import json
import os
import io
import wave
import websockets
import httpx
import requests
import structlog

logger = structlog.get_logger(__name__)

JARVIS_API = "http://localhost:8000"


def transcribe(audio_bytes: bytes) -> str:
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key or api_key in ("...", "dummy"):
        return ""
    try:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
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
        text = result["results"]["channels"][0]["alternatives"][0]["transcript"]
        logger.info("transcribed", text=text)
        return text.strip()
    except Exception as e:
        logger.error("transcribe_error", error=str(e))
        return ""


def get_tts_audio(text: str) -> bytes:
    api_key  = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    if not api_key or api_key in ("dummy", "..."):
        return b""
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
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
            timeout=30,
        )
        if response.status_code == 200:
            return response.content
        logger.error("tts_error", status=response.status_code)
        return b""
    except Exception as e:
        logger.error("tts_error", error=str(e))
        return b""


async def ask_jarvis(command: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{JARVIS_API}/agents/run",
                json={"command": command},
            )
            return response.json().get("response", "I could not process that.")
    except Exception as e:
        return f"Could not reach Jarvis: {e}"


async def handle_client(websocket):
    logger.info("client_connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "audio":
                # Browser sent audio data
                audio_b64 = data.get("audio", "")
                audio_bytes = base64.b64decode(audio_b64)

                # Send status
                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "transcribing"
                }))

                # Transcribe
                text = transcribe(audio_bytes)
                if not text:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Could not transcribe audio"
                    }))
                    continue

                # Send transcription to UI
                await websocket.send(json.dumps({
                    "type": "transcript",
                    "text": text
                }))

                # Process with Jarvis
                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "processing"
                }))
                response = await ask_jarvis(text)

                # Send text response
                await websocket.send(json.dumps({
                    "type": "response",
                    "text": response
                }))

                # Get TTS audio
                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "speaking"
                }))
                audio_data = get_tts_audio(response)
                if audio_data:
                    audio_b64 = base64.b64encode(audio_data).decode()
                    await websocket.send(json.dumps({
                        "type": "audio",
                        "audio": audio_b64,
                        "format": "mp3"
                    }))

                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "idle"
                }))

            elif msg_type == "text":
                # Text command from UI
                text = data.get("text", "")
                if not text:
                    continue

                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "processing"
                }))
                response = await ask_jarvis(text)

                await websocket.send(json.dumps({
                    "type": "response",
                    "text": response
                }))

                audio_data = get_tts_audio(response)
                if audio_data:
                    audio_b64 = base64.b64encode(audio_data).decode()
                    await websocket.send(json.dumps({
                        "type": "audio",
                        "audio": audio_b64,
                        "format": "mp3"
                    }))

                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "idle"
                }))

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logger.error("handler_error", error=str(e))
    finally:
        logger.info("client_disconnected")


async def main():
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("browser_voice_server.starting", port=8765)
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        logger.info("browser_voice_server.ready")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
