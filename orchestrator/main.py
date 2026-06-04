from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agents, health, runs, voice
from config.settings import get_settings
from orchestrator.brain import JarvisBrain

logger = structlog.get_logger(__name__)

brain = JarvisBrain()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("jarvis.starting")
    settings = get_settings()
    brain.initialise()
    app.state.brain = brain
    logger.info("jarvis.ready", env=settings.jarvis_env, port=settings.jarvis_api_port)
    yield
    logger.info("jarvis.shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Jarvis AI Ops Platform",
        description="Voice-controlled AI DevOps & Infra Platform — 15 agents",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="", tags=["health"])
    app.include_router(agents.router, prefix="/agents", tags=["agents"])
    app.include_router(runs.router, prefix="/runs", tags=["runs"])
    app.include_router(voice.router, prefix="/voice", tags=["voice"])

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "orchestrator.main:app",
        host="0.0.0.0",
        port=settings.jarvis_api_port,
        reload=not settings.is_production,
        log_level=settings.jarvis_log_level.lower(),
    )
