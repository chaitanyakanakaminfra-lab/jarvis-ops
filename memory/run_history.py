"""
memory/run_history.py
──────────────────────
Saves every agent run to Postgres for audit trail and reporting.
"""

import structlog
from agents.base_agent import AgentRun

logger = structlog.get_logger(__name__)


class RunHistory:

    @staticmethod
    async def save(run: AgentRun) -> None:
        """Save an agent run record to Postgres."""
        try:
            import asyncpg
            from config.settings import get_settings
            settings = get_settings()

            conn = await asyncpg.connect(settings.database_url)
            try:
                await conn.execute("""
                    INSERT INTO agent_runs (
                        run_id, agent_id, agent_name, command,
                        status, result, error, started_at,
                        finished_at, duration_ms, metadata
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        result = EXCLUDED.result,
                        error = EXCLUDED.error,
                        finished_at = EXCLUDED.finished_at,
                        duration_ms = EXCLUDED.duration_ms
                """,
                    str(run.run_id),
                    run.agent_id,
                    run.agent_name,
                    run.command,
                    run.status.value,
                    run.result,
                    run.error,
                    run.started_at,
                    run.finished_at,
                    run.duration_ms,
                    "{}",
                )
                logger.info("run_history.saved", run_id=run.run_id, agent=run.agent_id)
            finally:
                await conn.close()

        except Exception as e:
            logger.warning("run_history.save_failed", error=str(e))

    @staticmethod
    async def get_recent(limit: int = 20) -> list:
        """Get recent agent runs."""
        try:
            import asyncpg
            from config.settings import get_settings
            settings = get_settings()

            conn = await asyncpg.connect(settings.database_url)
            try:
                rows = await conn.fetch("""
                    SELECT run_id, agent_id, agent_name,
                           LEFT(command, 80) AS command,
                           status, duration_ms, started_at
                    FROM agent_runs
                    ORDER BY started_at DESC
                    LIMIT $1
                """, limit)
                return [dict(r) for r in rows]
            finally:
                await conn.close()
        except Exception as e:
            logger.warning("run_history.get_failed", error=str(e))
            return []

    @staticmethod
    async def get_stats() -> dict:
        """Get agent run statistics."""
        try:
            import asyncpg
            from config.settings import get_settings
            settings = get_settings()

            conn = await asyncpg.connect(settings.database_url)
            try:
                row = await conn.fetchrow("""
                    SELECT
                        COUNT(*) AS total_runs,
                        COUNT(*) FILTER (WHERE status='success') AS success_count,
                        COUNT(*) FILTER (WHERE status='failure') AS failure_count,
                        ROUND(AVG(duration_ms)) AS avg_duration_ms
                    FROM agent_runs
                """)
                return dict(row) if row else {}
            finally:
                await conn.close()
        except Exception as e:
            logger.warning("run_history.stats_failed", error=str(e))
            return {}
