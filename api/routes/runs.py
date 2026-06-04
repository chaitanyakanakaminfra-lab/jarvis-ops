from fastapi import APIRouter

router = APIRouter()

@router.get("/{run_id}")
async def get_run(run_id: str):
    return {"run_id": run_id, "status": "not_implemented_yet"}

@router.get("/")
async def list_runs():
    return {"runs": []}
