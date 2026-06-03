from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class AgentRunRequest(BaseModel):
    command: str
    agent_id: str | None = None


class AgentRunResponse(BaseModel):
    run_id: str
    agent_id: str
    response: str
    status: str


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(request: Request, body: AgentRunRequest):
    brain = request.app.state.brain
    try:
        response = await brain.process(body.command)
        return AgentRunResponse(
            run_id="auto",
            agent_id=body.agent_id or "auto-routed",
            response=response,
            status="success",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_agents():
    import yaml
    from pathlib import Path
    with open(Path("config/agent_registry.yaml")) as f:
        registry = yaml.safe_load(f)
    return {"agents": [
        {"id": a["id"], "name": a["name"], "category": a["category"]}
        for a in registry["agents"]
    ]}
