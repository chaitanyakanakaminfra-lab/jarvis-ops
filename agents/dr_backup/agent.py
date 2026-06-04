from agents.base_agent import BaseAgent

class DRBackupAgent(BaseAgent):
    agent_id   = "dr_backup"
    agent_name = "DR & Backup Agent"

    async def _run(self, command: str) -> str:
        return "DR & Backup agent is not yet implemented. Coming in Phase 3."
