from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.db.models import Account, Chat, Template


def accounts_pick_keyboard(accounts: list[Account], prefix: str = "pick") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"#{a.id} {a.name} ({a.role})", callback_data=f"{prefix}:acc:{a.id}")]
        for a in accounts[:12]
    ]
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def templates_pick_keyboard(templates: list[Template]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"#{t.id} {t.name[:28]}", callback_data=f"cu:tpl:{t.id}")]
        for t in templates[:12]
    ]
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chats_multiselect_keyboard(
    chats: list[Chat],
    selected: set[int],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for chat in chats[:15]:
        mark = "✅" if chat.id in selected else "⬜"
        title = (chat.title or "?")[:26]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} #{chat.id} {title}",
                    callback_data=f"cu:cht:{chat.id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=f"✔️ Готово ({len(selected)})",
                callback_data="cu:cht:done",
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def campaign_preset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🐢 Безопасно (15–30 сек)",
                    callback_data="cu:preset:safe",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Быстрее (10–20 сек)",
                    callback_data="cu:preset:fast",
                )
            ],
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")],
        ]
    )


def campaign_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Запустить", callback_data="cu:confirm")],
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")],
        ]
    )


def campaigns_control_keyboard(campaign_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏸ Пауза", callback_data=f"cmp:pause:{campaign_id}"),
                InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"cmp:resume:{campaign_id}"),
            ],
            [InlineKeyboardButton(text="⏹ Стоп", callback_data=f"cmp:stop:{campaign_id}")],
            [InlineKeyboardButton(text="📊 Отчёт", callback_data=f"cmp:report:{campaign_id}")],
        ]
    )
