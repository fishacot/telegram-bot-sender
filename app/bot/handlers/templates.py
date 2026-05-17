from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from sqlalchemy import select

from app.infrastructure.db.models import TeamStep, Template
from app.infrastructure.db.session import SessionLocal

router = Router()


@router.message(Command("templates"))
async def templates_handler(message: Message) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(Template).where(Template.is_active.is_(True)))
        templates = list(result.scalars().all())
    if not templates:
        await message.answer("No templates. Add: /template_add <name> <text body>")
        return
    lines = [f"#{t.id} {t.name} kind={t.kind}" for t in templates]
    await message.answer("Templates:\n" + "\n".join(lines))


@router.message(Command("template_add"))
async def template_add_handler(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /template_add <name> <body text>")
        return
    name, body = parts[1], parts[2]
    async with SessionLocal() as session:
        template = Template(name=name, kind="text", body=body, variables_json={}, is_active=True)
        session.add(template)
        await session.commit()
        await session.refresh(template)
    await message.answer(f"Template #{template.id} created.")


@router.message(Command("team_step_add"))
async def team_step_add_handler(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=5)
    if len(parts) < 6:
        await message.answer(
            "Usage: /team_step_add <template_id> <step_no> <role> <delay_sec> <text...>"
        )
        return
    template_id = int(parts[1])
    step_no = int(parts[2])
    role = parts[3]
    delay_sec = int(parts[4])
    text = parts[5]
    if not text:
        await message.answer("Provide step text.")
        return
    async with SessionLocal() as session:
        template = await session.get(Template, template_id)
        if not template:
            await message.answer("Template not found.")
            return
        template.kind = "team"
        session.add(
            TeamStep(
                template_id=template_id,
                step_no=step_no,
                role=role,
                text=text,
                delay_sec=delay_sec,
                reply_to_prev=False,
            )
        )
        await session.commit()
    await message.answer(f"Team step {step_no} added to template {template_id}.")
