"""Optional demo seed for local testing."""
import asyncio

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Account, AccountPack, AccountPackItem, Chat, TeamStep, Template
from app.infrastructure.db.session import SessionLocal, engine


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(Account(name="acc1", session_path="acc1", role="lead"))
        session.add(Account(name="acc2", session_path="acc2", role="support"))
        session.add(
            Chat(
                tg_chat_id=-1001234567890,
                title="Demo Group",
                type="supergroup",
                can_send=True,
            )
        )
        text_tpl = Template(name="welcome", kind="text", body="Hello from {shop}", variables_json={"shop": "ShopX"})
        team_tpl = Template(name="team_dialog", kind="team", body="team", variables_json={"shop": "ShopX", "city": "Berlin"})
        session.add_all([text_tpl, team_tpl])
        await session.flush()
        session.add(TeamStep(template_id=team_tpl.id, step_no=1, role="lead", text="Hi from {shop}", delay_sec=0))
        session.add(
            TeamStep(
                template_id=team_tpl.id,
                step_no=2,
                role="support",
                text="We operate in {city}",
                delay_sec=15,
                reply_to_prev=True,
            )
        )
        pack = AccountPack(name="default")
        session.add(pack)
        await session.flush()
        session.add(AccountPackItem(pack_id=pack.id, account_id=1))
        session.add(AccountPackItem(pack_id=pack.id, account_id=2))
        await session.commit()
    print("Seed complete: accounts, chats, templates, team steps, pack")


if __name__ == "__main__":
    asyncio.run(seed())
