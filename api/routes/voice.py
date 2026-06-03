import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()


class VoiceCommandRequest(BaseModel):
    text: str


class VoiceCommandResponse(BaseModel):
    response: str
    agent_used: str | None = None


@router.post("/command", response_model=VoiceCommandResponse)
async def voice_command(body: VoiceCommandRequest, request=None):
    return VoiceCommandResponse(
        response=f"Processing: {body.text}",
        agent_used="auto-routed",
    )


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")
            content = message.get("content", "")

            if msg_type == "text":
                await websocket.send_text(json.dumps({"type": "status", "content": "processing"}))
                response = f"Received: {content}"
                await websocket.send_text(json.dumps({"type": "response", "content": response}))
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
