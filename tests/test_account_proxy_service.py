import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Account
from app.infrastructure.telethon_clients.factory import TelethonClientFactory
from app.services.account_proxy_service import AccountProxyService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


@pytest.fixture
def service(session: AsyncSession) -> AccountProxyService:
    factory = TelethonClientFactory(
        sessions_dir="sessions",
        api_id=1,
        api_hash="hash",
    )
    return AccountProxyService(session, factory)


@pytest.mark.asyncio
async def test_bulk_assign_by_order(session, service):
    session.add_all(
        [
            Account(name="a1", session_path="a1", is_active=True),
            Account(name="a2", session_path="a2", is_active=True),
            Account(name="a3", session_path="a3", is_active=True),
        ]
    )
    await session.commit()

    result = await service.bulk_assign_by_order(
        "socks5://1.1.1.1:1080\n2.2.2.2:1080\n"
    )
    assert len(result.updated) == 2
    assert result.unchanged_account_names == ["a3"]


@pytest.mark.asyncio
async def test_bulk_assign_round_robin(session, service):
    session.add_all(
        [
            Account(name="a1", session_path="a1", is_active=True),
            Account(name="a2", session_path="a2", is_active=True),
            Account(name="a3", session_path="a3", is_active=True),
        ]
    )
    await session.commit()

    result = await service.bulk_assign_round_robin(
        "socks5://1.1.1.1:1080\nsocks5://2.2.2.2:1080\n"
    )
    assert len(result.updated) == 3
    assert result.updated[0][2] != result.updated[1][2]
    assert result.updated[2][2] == result.updated[0][2]

    row = await session.get(Account, result.updated[0][0])
    assert row and row.proxy
