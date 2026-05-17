from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Account, AccountPack, AccountPackItem


class AccountPackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def resolve_account_ids(self, pack_ids: list[int]) -> list[int]:
        if not pack_ids:
            return []
        result = await self.session.execute(
            select(AccountPackItem.account_id).where(AccountPackItem.pack_id.in_(pack_ids))
        )
        account_ids = sorted({row[0] for row in result.fetchall()})
        return account_ids

    async def list_packs(self) -> list[AccountPack]:
        result = await self.session.execute(select(AccountPack).order_by(AccountPack.id))
        return list(result.scalars().all())

    async def validate_account_ids(self, account_ids: list[int]) -> list[int]:
        if not account_ids:
            return []
        result = await self.session.execute(
            select(Account.id).where(Account.id.in_(account_ids), Account.is_active.is_(True))
        )
        found = {row[0] for row in result.fetchall()}
        return [item for item in account_ids if item not in found]
