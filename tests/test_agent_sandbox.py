import pytest

from app.infrastructure.agent.sandbox import AgentSandbox, AgentSandboxError, redact_secrets


def test_redact_secrets():
    text = "BOT_TOKEN=123456:ABCDEFghijklmnopqrstuvwxyz1234567890"
    assert "[REDACTED]" in redact_secrets(text)


def test_sandbox_blocks_env(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".env").write_text("BOT_TOKEN=secret", encoding="utf-8")
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text("print('ok')", encoding="utf-8")
    sandbox = AgentSandbox(str(root))
    sandbox.read_text("app/main.py")
    with pytest.raises(AgentSandboxError):
        sandbox.read_text(".env")


def test_sandbox_write_report(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    sandbox = AgentSandbox(str(root))
    path = sandbox.write_report("test_report.md", "# hello")
    assert path.exists()
    assert "hello" in path.read_text(encoding="utf-8")
