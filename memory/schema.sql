CREATE TABLE IF NOT EXISTS agent_runs (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(64)  NOT NULL,
    agent_name      VARCHAR(128) NOT NULL,
    command         TEXT         NOT NULL,
    status          VARCHAR(16)  NOT NULL CHECK (status IN ('success','failure','running','skipped')),
    result          TEXT,
    error           TEXT,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    metadata        JSONB        DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id   ON agent_runs (agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status     ON agent_runs (status);

CREATE TABLE IF NOT EXISTS voice_sessions (
    session_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    turns       JSONB DEFAULT '[]'::jsonb,
    agent_runs  UUID[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start      DATE NOT NULL,
    week_end        DATE NOT NULL,
    total_runs      INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs     INTEGER DEFAULT 0,
    agents_used     JSONB DEFAULT '{}'::jsonb,
    cost_summary    JSONB DEFAULT '{}'::jsonb,
    incidents       INTEGER DEFAULT 0,
    report_text     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW recent_agent_runs AS
    SELECT run_id, agent_id, agent_name,
           LEFT(command, 80) AS command_preview,
           status, duration_ms, started_at
    FROM agent_runs ORDER BY started_at DESC LIMIT 100;

CREATE OR REPLACE VIEW agent_stats AS
    SELECT agent_id, agent_name,
           COUNT(*) AS total_runs,
           COUNT(*) FILTER (WHERE status = 'success') AS success_count,
           COUNT(*) FILTER (WHERE status = 'failure') AS failure_count,
           ROUND(AVG(duration_ms)) AS avg_duration_ms,
           MAX(started_at) AS last_run_at
    FROM agent_runs GROUP BY agent_id, agent_name ORDER BY total_runs DESC;
