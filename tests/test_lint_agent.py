"""
tests/test_lint_agent.py
Run: pytest tests/test_lint_agent.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def agent():
    with patch("agents.base_agent.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(jarvis_voice_enabled=False)
        from agents.lint.agent import LintAgent
        return LintAgent()


class TestClassify:
    def test_ruff(self):
        from agents.lint.agent import _classify
        assert _classify("run ruff on agents/")["tool"].value == "ruff"

    def test_shellcheck(self):
        from agents.lint.agent import _classify
        assert _classify("run shellcheck")["tool"].value == "shellcheck"

    def test_ansible(self):
        from agents.lint.agent import _classify
        assert _classify("run ansible-lint")["tool"].value == "ansible-lint"

    def test_run_all(self):
        from agents.lint.agent import _classify
        assert _classify("run all linters")["action"] == "run_all"

    def test_trigger(self):
        from agents.lint.agent import _classify
        assert _classify("trigger ruff workflow")["action"] == "trigger"

    def test_unknown(self):
        from agents.lint.agent import _classify
        assert _classify("make me a sandwich")["action"] == "unknown"


class TestLintAgentRun:
    @pytest.mark.asyncio
    async def test_ruff_clean(self, agent):
        with patch("agents.lint.agent._run_ruff", return_value={"tool": "ruff", "exit_code": 0, "issues": [], "issue_count": 0}):
            result = await agent.execute("run ruff on agents/")
        assert any(w in result.lower() for w in ("zero", "clean", "no issues"))

    @pytest.mark.asyncio
    async def test_ruff_issues(self, agent):
        with patch("agents.lint.agent._run_ruff", return_value={"tool": "ruff", "exit_code": 1, "issues": [{}]*3, "issue_count": 3}):
            result = await agent.execute("run ruff")
        assert "3" in result

    @pytest.mark.asyncio
    async def test_trigger_no_token(self, agent):
        agent._github_token = ""
        result = await agent.execute("trigger ruff workflow")
        assert "token" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_command(self, agent):
        result = await agent.execute("make me a sandwich")
        assert len(result) > 0
