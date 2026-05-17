from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Account


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_accounts(self) -> list[Account]:
        result = await self.session.execute(select(Account).where(Account.is_active.is_(True)))
        return list(result.scalars().all())

    async def set_health_status(self, account_id: int, status: str) -> None:
        account = await self.session.get(Account, account_id)
        if not account:
            return
        account.health_status = status
        await self.session.commit()
