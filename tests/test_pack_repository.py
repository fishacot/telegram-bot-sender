import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Account, AccountPack, AccountPackItem
from app.infrastructure.repositories.account_pack_repository import AccountPackRepository


@pytest.mark.asyncio
async def test_pack_resolve_account_ids() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        pack = AccountPack(name="main")
        session.add(pack)
        await session.flush()
        session.add(Account(name="a1", session_path="a1", role="lead"))
        session.add(Account(name="a2", session_path="a2", role="support"))
        await session.flush()
        session.add(AccountPackItem(pack_id=pack.id, account_id=1))
        session.add(AccountPackItem(pack_id=pack.id, account_id=2))
        await session.commit()

        repo = AccountPackRepository(session)
        resolved = await repo.resolve_account_ids([pack.id])
        assert resolved == [1, 2]

    await engine.dispose()
