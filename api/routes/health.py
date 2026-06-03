from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "0.1.0"
    brain_ready: bool


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    brain = getattr(request.app.state, "brain", None)
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        brain_ready=brain is not None and brain._executor is not None,
    )


@router.get("/ready")
async def ready(request: Request):
    brain = getattr(request.app.state, "brain", None)
    if not brain or not brain._executor:
        return {"status": "not_ready", "reason": "brain_not_initialised"}
    return {"status": "ready"}
