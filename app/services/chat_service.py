from app.infrastructure.repositories.chat_repository import ChatRepository


class ChatService:
    def __init__(self, repository: ChatRepository) -> None:
        self.repository = repository

    async def list_compliant_chats(self):
        return await self.repository.list_compliant_chats()
