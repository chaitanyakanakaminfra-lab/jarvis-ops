"""
api/routes/runs.py
───────────────────
Run history endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RunResponse(BaseModel):
    run_id: str
    agent_id: str
    agent_name: str
    command: str
    status: str
    duration_ms: int | None = None
    started_at: str | None = None


@router.get("/")
async def list_runs(limit: int = 20):
    """List recent agent runs."""
    try:
        from memory.run_history import RunHistory
        runs = await RunHistory.get_recent(limit=limit)
        return {"runs": runs, "count": len(runs)}
    except Exception as e:
        return {"runs": [], "count": 0, "error": str(e)}


@router.get("/stats")
async def run_stats():
    """Get agent run statistics."""
    try:
        from memory.run_history import RunHistory
        stats = await RunHistory.get_stats()
        return stats
    except Exception as e:
        return {"error": str(e)}


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get a specific run by ID."""
    return {"run_id": run_id, "status": "not_implemented_yet"}
