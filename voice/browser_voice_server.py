import asyncio
import base64
import json
import os
import io
import ssl
import wave
import websockets
import httpx
import requests
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)
JARVIS_API = "http://localhost:8000"
active_client = None


def transcribe(audio_bytes: bytes) -> str:
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key or api_key in ("...", "dummy"):
        return ""
    try:
        response = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&language=en",
            headers={"Authorization": f"Token {api_key}", "Content-Type": "audio/webm"},
            data=audio_bytes,
            timeout=30,
        )
        text = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
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
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_turbo_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.content
        return b""
    except Exception as e:
        logger.error("tts_error", error=str(e))
        return b""


async def speak(websocket, text: str):
    """Send TTS audio to client."""
    logger.info("speaking", text=text[:50])
    audio_data = get_tts_audio(text)
    if audio_data:
        await websocket.send(json.dumps({
            "type": "audio",
            "audio": base64.b64encode(audio_data).decode(),
            "format": "mp3"
        }))


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
    global active_client
    if active_client and active_client != websocket:
        try:
            await active_client.close()
        except:
            pass
    active_client = websocket
    logger.info("client_connected")

    jarvis_awake = False

    try:
        async for message in websocket:
            data     = json.loads(message)
            msg_type = data.get("type")
            logger.info("message_received", type=msg_type)

            # ── Audio from mic ────────────────────────────────────────────────
            if msg_type == "audio":
                audio_bytes = base64.b64decode(data.get("audio", ""))
                await websocket.send(json.dumps({"type": "status", "message": "transcribing"}))
                text = transcribe(audio_bytes)

                if not text:
                    await websocket.send(json.dumps({"type": "status", "message": "idle"}))
                    continue

                await websocket.send(json.dumps({"type": "transcript", "text": text}))
                text_lower = text.lower().strip()
                logger.info("processing_text", text=text_lower, awake=jarvis_awake)

                # Hey Jarvis — wake up
                if any(w in text_lower for w in ["hey jarvis", "hi jarvis", "jarvis wake", "okay jarvis", "ok jarvis"]):
                    jarvis_awake = True
                    hour = datetime.now().hour
                    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
                    response = f"{greeting} Chaitanya. I am online and ready. What would you like me to do?"
                    await websocket.send(json.dumps({"type": "response", "text": response}))
                    await speak(websocket, response)
                    await websocket.send(json.dumps({"type": "status", "message": "idle"}))
                    continue

                # Wake up all agents
                if any(w in text_lower for w in ["wake up all", "wakeup all", "all agents", "wake all", "start all", "briefing", "morning briefing", "pick up all"]):
                    jarvis_awake = True
                    response = "Waking up all agents now. Stand by."
                    await websocket.send(json.dumps({"type": "response", "text": response}))
                    await speak(websocket, response)
                    await websocket.send(json.dumps({"type": "briefing_trigger"}))
                    await websocket.send(json.dumps({"type": "status", "message": "idle"}))
                    continue

                # Sleep
                if any(w in text_lower for w in ["sleep", "goodbye", "go to sleep", "standby", "go to standby"]):
                    jarvis_awake = False
                    response = "Going to standby. Call me when you need me, Chaitanya."
                    await websocket.send(json.dumps({"type": "response", "text": response}))
                    await speak(websocket, response)
                    await websocket.send(json.dumps({"type": "status", "message": "idle"}))
                    continue

                # If not awake — ignore
                if not jarvis_awake:
                    await websocket.send(json.dumps({"type": "status", "message": "idle"}))
                    continue

                # Regular command
                await websocket.send(json.dumps({"type": "status", "message": "processing"}))
                response = await ask_jarvis(text)
                await websocket.send(json.dumps({"type": "response", "text": response}))
                await speak(websocket, response)
                await websocket.send(json.dumps({"type": "status", "message": "idle"}))

            # ── Direct TTS request from UI ────────────────────────────────────
            elif msg_type == "tts":
                text = data.get("text", "")
                if text:
                    logger.info("tts_request", text=text[:50])
                    await speak(websocket, text)

            # ── Text command from UI ──────────────────────────────────────────
            elif msg_type == "text":
                text = data.get("text", "")
                if not text:
                    continue
                text_lower = text.lower()
                if any(w in text_lower for w in ["wake up all", "all agents", "briefing"]):
                    await websocket.send(json.dumps({"type": "briefing_trigger"}))
                    continue
                await websocket.send(json.dumps({"type": "status", "message": "processing"}))
                response = await ask_jarvis(text)
                await websocket.send(json.dumps({"type": "response", "text": response}))
                await speak(websocket, response)
                await websocket.send(json.dumps({"type": "status", "message": "idle"}))

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logger.error("handler_error", error=str(e))
    finally:
        if active_client == websocket:
            globals()["active_client"] = None
        logger.info("client_disconnected")


async def main():
    from dotenv import load_dotenv
    load_dotenv()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile="/home/ubuntu/jarvis-ops/certs/fullchain.pem",
        keyfile="/home/ubuntu/jarvis-ops/certs/privkey.pem",
    )

    logger.info("browser_voice_server.starting", port=8765, ssl=True)
    async with websockets.serve(handle_client, "0.0.0.0", 8765, ssl=ssl_context):
        logger.info("browser_voice_server.ready")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
