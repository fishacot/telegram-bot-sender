import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.infrastructure.agent.sandbox import AgentSandbox
from app.infrastructure.ai_provider.stub_provider import StubAiProvider
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import AgentErrorEvent
from app.services.project_agent_service import ProjectAgentService


@pytest.fixture
async def session(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(
            AgentErrorEvent(
                source="test",
                level="ERROR",
                message="Connection timeout",
                traceback=None,
                context_json={},
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


@pytest.fixture
def service(session, tmp_path) -> ProjectAgentService:
    settings = Settings(
        BOT_TOKEN="123456:ABCDEFghijklmnopqrstuvwxyz1234567890",
        ADMIN_IDS="1",
        PROJECT_ROOT=str(tmp_path),
        AI_AGENT_ENABLED=True,
    )
    sandbox = AgentSandbox(str(tmp_path))
    return ProjectAgentService(session, settings, StubAiProvider(), sandbox)


@pytest.mark.asyncio
async def test_diagnose_errors(service):
    result = await service.diagnose_errors(limit=5)
    assert result.get("summary") or result.get("risk")
    assert "report_file" in result
