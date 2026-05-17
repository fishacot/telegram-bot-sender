from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Chat


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_chat(self, chat_id: int) -> Chat | None:
        return await self.session.get(Chat, chat_id)

    async def list_compliant_chats(self) -> list[Chat]:
        result = await self.session.execute(
            select(Chat).where(
                Chat.is_archived.is_(False),
                Chat.is_blacklisted.is_(False),
                Chat.type.in_(["group", "supergroup", "channel"]),
            )
        )
        return list(result.scalars().all())
