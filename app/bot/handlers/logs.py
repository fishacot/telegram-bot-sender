from aiogram import Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.bot.keyboards.builders import nav_row
from app.infrastructure.db.models import AgentErrorEvent, AuditEvent, JoinTask
from app.infrastructure.db.session import SessionLocal

router = Router()


async def build_logs_text() -> str:
    async with SessionLocal() as session:
        audit = await session.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(8))
        joins = await session.execute(select(JoinTask).order_by(JoinTask.id.desc()).limit(5))
        errors = await session.execute(
            select(AgentErrorEvent).order_by(AgentErrorEvent.id.desc()).limit(5)
        )

    audit_lines = [
        f"• {e.action} (#{e.actor_id})" for e in audit.scalars().all()
    ]
    join_lines = [
        f"• #{j.id} acc{j.account_id} {j.status}" for j in joins.scalars().all()
    ]
    error_lines = [
        f"• [{e.level}] {e.message[:60]}" for e in errors.scalars().all()
    ]

    return (
        "📜 <b>Журнал</b>\n\n"
        "<b>Действия:</b>\n" + ("\n".join(audit_lines) or "—") + "\n\n"
        "<b>Вступления в чаты:</b>\n" + ("\n".join(join_lines) or "—") + "\n\n"
        "<b>Ошибки (агент):</b>\n" + ("\n".join(error_lines) or "—")
    )


def logs_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🤖 Разбор ошибок", callback_data="ag:diagnose")],
    ]
    nav = nav_row(back="nav:home", home=False)
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_logs_screen(message: Message, *, edit: bool = False) -> None:
    text = await build_logs_text()
    markup = logs_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)
