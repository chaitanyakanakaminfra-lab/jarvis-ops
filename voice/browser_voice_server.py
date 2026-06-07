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


# Agent voice map — each Marvel agent has unique voice
AGENT_VOICES = {
    "iron man":        "aura-zeus-en",
    "vision":          "aura-arcas-en",
    "war machine":     "aura-orion-en",
    "nick fury":       "aura-orion-en",
    "thor":            "aura-zeus-en",
    "cap america":     "aura-zeus-en",
    "captain america": "aura-zeus-en",
    "black widow":     "aura-athena-en",
    "hulk":            "aura-orion-en",
    "ant-man":         "aura-angus-en",
    "ant man":         "aura-angus-en",
    "giant-man":       "aura-arcas-en",
    "giant man":       "aura-arcas-en",
    "black panther":   "aura-zeus-en",
    "cap marvel":      "aura-asteria-en",
    "captain marvel":  "aura-asteria-en",
    "hawkeye":         "aura-arcas-en",
    "spider-man":      "aura-arcas-en",
    "spider man":      "aura-arcas-en",
    "doctor strange":  "aura-zeus-en",
    "dr strange":      "aura-zeus-en",
    "jarvis":          "aura-orion-en",
}

def get_tts_audio(text: str, voice: str = "aura-orion-en") -> bytes:
    """Deepgram TTS — unique voice per agent"""
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key:
        return b""
    try:
        response = requests.post(
            f"https://api.deepgram.com/v1/speak?model={voice}",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json",
            },
            json={"text": text},
            timeout=30,
        )
        if response.status_code == 200:
            logger.info("deepgram_tts_ok", voice=voice, bytes=len(response.content))
            return response.content
        logger.error("deepgram_tts_error", status=response.status_code, voice=voice)
        return b""
    except Exception as e:
        logger.error("tts_error", error=str(e))
        return b""


async def speak(websocket, text: str, agent_name: str = "jarvis"):
    """Send TTS audio to client."""
    logger.info("speaking", text=text[:50])
    voice = AGENT_VOICES.get(agent_name.lower(), "aura-orion-en")
    audio_data = get_tts_audio(text, voice=voice)
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
                # Single agent detection
                marvel_map = {
                    "iron man":      "cicd",
                    "vision":        "lint",
                    "war machine":   "docker",
                    "nick fury":     "release",
                    "thor":          "infra",
                    "store":         "infra",
                    "sir":           "infra",
                    "four":          "infra",
                    "door":          "infra",
                    "captain america": "kubernetes",
                    "cap america":   "kubernetes",
                    "black widow":   "cloud",
                    "hulk":          "backup",
                    "ant man":       "cost",
                    "ant-man":       "cost",
                    "antman":        "cost",
                    "giant man":     "scaling",
                    "giant-man":     "scaling",
                    "black panther": "security",
                    "captain marvel":"compliance",
                    "cap marvel":    "compliance",
                    "hawkeye":       "observe",
                    "hawk eye":      "observe",
                    "hockey":        "observe",
                    "hot guy":       "observe",
                    "spider man":    "incident",
                    "spider-man":    "incident",
                    "spiderman":     "incident",
                    "doctor strange":"reporting",
                    "dr strange":    "reporting",
                }

                activated_agent = None
                for name, agent_id in marvel_map.items():
                    if name in text_lower:
                        activated_agent = {"id": agent_id, "marvel": name.title()}
                        break

                if activated_agent:
                    await websocket.send(json.dumps({
                        "type": "single_agent_trigger",
                        "agent": activated_agent["id"],
                        "marvel": activated_agent["marvel"],
                    }))
                    response = f"Waking up {activated_agent['marvel']} now."
                    await speak(websocket, response, agent_name=activated_agent['marvel'])
                    await websocket.send(json.dumps({"type": "status", "message": "idle"}))
                    continue

                if any(w in text_lower for w in ["wake up all", "wakeup all", "all agents", "wake all", "start all", "briefing", "morning briefing", "pick up all", "pick up our", "pick up the", "wake our", "wake the", "all avengers", "assemble", "wake everyone", "start agents", "run all", "activate all"]):
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
                    agent_name = "jarvis"
                    text_lower_tts = text.lower()
                    for name in AGENT_VOICES.keys():
                        if name in text_lower_tts:
                            agent_name = name
                            break
                    voice = AGENT_VOICES.get(agent_name, "aura-orion-en")
                    logger.info("speaking", text=text[:50], voice=voice)
                    audio_data = get_tts_audio(text, voice=voice)
                    if audio_data:
                        b64 = base64.b64encode(audio_data).decode("utf-8")
                        await websocket.send(json.dumps({"type": "audio", "audio": b64}))

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

            elif msg_type == "wake":
                # UI woke Jarvis via clap — sync state
                jarvis_awake = True
                logger.info("jarvis_awake_via_clap")

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logger.error("handler_error", error=str(e))
    finally:
        logger.info("client_disconnected")


async def health_server():
    """Simple HTTP health check on port 8766"""
    from aiohttp import web
    async def health(request):
        return web.Response(text="ok")
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    app.router.add_get("/voice-ws", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8766)
    await site.start()
    logger.info("health_server.started", port=8766)

async def main():
    from dotenv import load_dotenv
    load_dotenv()

    # SSL optional — use certs if on EC2, skip in containers
    ssl_context = None
    cert = "/home/ubuntu/jarvis-ops/certs/fullchain.pem"
    key  = "/home/ubuntu/jarvis-ops/certs/privkey.pem"
    if os.path.exists(cert) and os.path.exists(key):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=cert, keyfile=key)

    logger.info("browser_voice_server.starting", port=8765, ssl=ssl_context is not None)
    async with websockets.serve(handle_client, "0.0.0.0", 8765, ssl=ssl_context):
        logger.info("browser_voice_server.ready")
        await asyncio.gather(
            asyncio.Future(),
            health_server(),
        )


if __name__ == "__main__":
    asyncio.run(main())
