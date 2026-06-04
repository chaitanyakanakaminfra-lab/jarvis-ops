"""
voice/briefing_server.py
─────────────────────────
WebSocket server that connects the JARVIS UI to the briefing system.
Streams real-time updates to the React dashboard as each agent is checked.
"""

import asyncio
import json
import websockets
import structlog

logger = structlog.get_logger(__name__)

CONNECTED_CLIENTS = set()


async def broadcast(message: dict) -> None:
    """Send message to all connected UI clients."""
    if CONNECTED_CLIENTS:
        data = json.dumps(message)
        await asyncio.gather(
            *[client.send(data) for client in CONNECTED_CLIENTS],
            return_exceptions=True,
        )


async def handle_client(websocket) -> None:
    """Handle a connected UI client."""
    CONNECTED_CLIENTS.add(websocket)
    logger.info("briefing_server.client_connected",
                total=len(CONNECTED_CLIENTS))
    try:
        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif data.get("type") == "text":
                # User typed a command
                command = data.get("content", "")
                logger.info("briefing_server.command", command=command)

                # Check if it's a wake/briefing command
                if any(w in command.lower() for w in
                       ["wake up", "morning", "briefing", "good morning"]):
                    from voice.morning_briefing import MorningBriefing
                    briefing = MorningBriefing()
                    await briefing.run(websocket_callback=broadcast)
                else:
                    # Regular command — send to Jarvis API
                    import httpx
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.post(
                            "http://localhost:8000/agents/run",
                            json={"command": command},
                        )
                        result = response.json()
                        await broadcast({
                            "type": "response",
                            "message": result.get("response", ""),
                        })

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        logger.info("briefing_server.client_disconnected",
                    total=len(CONNECTED_CLIENTS))


async def main():
    logger.info("briefing_server.starting", port=8080)
    async with websockets.serve(handle_client, "0.0.0.0", 8080):
        logger.info("briefing_server.ready")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
