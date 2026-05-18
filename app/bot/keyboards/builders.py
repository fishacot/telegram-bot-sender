from __future__ import annotations

import math

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.db.models import Account, Campaign, Chat, Template

PER_PAGE_DEFAULT = 8
CHATS_PER_PAGE = 10
CAMPAIGNS_PER_PAGE = 5


def _paginate_row(prefix: str, page: int, total_pages: int) -> list[InlineKeyboardButton] | None:
    if total_pages <= 1:
        return None
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:p:{page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:p:{page + 1}"))
    return buttons


def nav_row(*, back: str | None = None, home: bool = True) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if back:
        row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=back))
    if home:
        row.append(InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home"))
    return row


def dashboard_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Аккаунты", callback_data="go:acc"),
                InlineKeyboardButton(text="💬 Чаты", callback_data="go:cht"),
            ],
            [
                InlineKeyboardButton(text="📝 Шаблоны", callback_data="go:tpl"),
                InlineKeyboardButton(text="📤 Рассылка", callback_data="go:campaign"),
            ],
            [
                InlineKeyboardButton(text="📋 Рассылки", callback_data="go:campaigns"),
                InlineKeyboardButton(text="🤖 Агент", callback_data="go:agent"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="tool:settings"),
                InlineKeyboardButton(text="📜 Журнал", callback_data="tool:logs"),
            ],
        ]
    )


def section_agent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Разбор ошибок", callback_data="ag:diagnose"),
                InlineKeyboardButton(text="📄 Полный отчёт", callback_data="ag:report"),
            ],
            [
                InlineKeyboardButton(text="💬 Спросить", callback_data="ag:ask"),
                InlineKeyboardButton(text="ℹ️ Статус", callback_data="ag:status"),
            ],
            nav_row(home=True),
        ]
    )


def setup_gap_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Аккаунт", callback_data="go:acc"),
                InlineKeyboardButton(text="🌐 Прокси", callback_data="acc:proxy_menu"),
            ],
            [
                InlineKeyboardButton(text="➕ Чат", callback_data="go:cht"),
                InlineKeyboardButton(text="➕ Шаблон", callback_data="go:tpl"),
            ],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home")],
        ]
    )


def section_accounts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Загрузить .session", callback_data="acc:upload")],
            [InlineKeyboardButton(text="🌐 Прокси", callback_data="acc:proxy_menu")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="acc:list:p:0")],
            nav_row(home=True),
        ]
    )


def section_proxy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 N прокси → все аккаунты", callback_data="acc:proxy_rotate")],
            [InlineKeyboardButton(text="📋 1 строка = 1 аккаунт", callback_data="acc:proxy_bulk")],
            [InlineKeyboardButton(text="♻️ Один прокси на всех", callback_data="acc:proxy_all")],
            [InlineKeyboardButton(text="👤 Один аккаунт", callback_data="acc:proxy")],
            nav_row(back="acc:list:p:0", home=True),
        ]
    )


def section_chats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить чат", callback_data="cht:add")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="cht:list:p:0")],
            nav_row(home=True),
        ]
    )


def section_templates_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Новый шаблон", callback_data="tpl:add")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="tpl:list:p:0")],
            nav_row(home=True),
        ]
    )


def paginated_section_keyboard(
    prefix: str,
    page: int,
    total_pages: int,
    section_markup: InlineKeyboardMarkup,
) -> InlineKeyboardMarkup:
    rows = list(section_markup.inline_keyboard)
    pager = _paginate_row(f"{prefix}:list", page, total_pages)
    if pager:
        rows.insert(0, pager)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def accounts_pick_keyboard(
    accounts: list[Account],
    *,
    prefix: str = "pick",
    page: int = 0,
    per_page: int = PER_PAGE_DEFAULT,
    back: str | None = None,
) -> InlineKeyboardMarkup:
    total_pages = max(1, math.ceil(len(accounts) / per_page))
    page = min(page, total_pages - 1)
    start = page * per_page
    chunk = accounts[start : start + per_page]
    rows = [
        [InlineKeyboardButton(text=f"#{a.id} {a.name}", callback_data=f"{prefix}:acc:{a.id}")]
        for a in chunk
    ]
    pager = _paginate_row(f"{prefix}:list", page, total_pages)
    if pager:
        rows.append(pager)
    nav = nav_row(back=back, home=True)
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def templates_pick_keyboard(
    templates: list[Template],
    *,
    page: int = 0,
    per_page: int = PER_PAGE_DEFAULT,
) -> InlineKeyboardMarkup:
    total_pages = max(1, math.ceil(len(templates) / per_page))
    page = min(page, total_pages - 1)
    start = page * per_page
    chunk = templates[start : start + per_page]
    rows = [
        [InlineKeyboardButton(text=f"#{t.id} {t.name[:28]}", callback_data=f"cu:tpl:{t.id}")]
        for t in chunk
    ]
    pager = _paginate_row("cu:tpl", page, total_pages)
    if pager:
        rows.append(pager)
    rows.append(nav_row(back="cu:back:tpl", home=True))
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chats_multiselect_keyboard(
    chats: list[Chat],
    selected: set[int],
    *,
    page: int = 0,
    per_page: int = CHATS_PER_PAGE,
) -> InlineKeyboardMarkup:
    total_pages = max(1, math.ceil(len(chats) / per_page))
    page = min(page, total_pages - 1)
    start = page * per_page
    chunk = chats[start : start + per_page]
    rows: list[list[InlineKeyboardButton]] = []
    for chat in chunk:
        mark = "✅" if chat.id in selected else "⬜"
        title = (chat.title or "?")[:24]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} #{chat.id} {title}",
                    callback_data=f"cu:cht:{chat.id}",
                )
            ]
        )
    pager = _paginate_row("cu:cht", page, total_pages)
    if pager:
        rows.append(pager)
    rows.append(
        [
            InlineKeyboardButton(text="✅ Все на странице", callback_data=f"cu:cht:all:{page}"),
            InlineKeyboardButton(text="⬜ Сброс", callback_data="cu:cht:clear"),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=f"✔️ Готово ({len(selected)})", callback_data="cu:cht:done")]
    )
    rows.append(nav_row(back="cu:back:cht", home=True))
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def campaign_preset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐢 Безопасно (15–30 сек)", callback_data="cu:preset:safe")],
            [InlineKeyboardButton(text="⚡ Быстрее (10–20 сек)", callback_data="cu:preset:fast")],
            nav_row(back="cu:back:tpl", home=True),
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")],
        ]
    )


def campaign_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Запустить", callback_data="cu:confirm")],
            nav_row(back="cu:back:confirm", home=True),
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="cu:cancel")],
        ]
    )


def campaigns_list_keyboard(campaigns: list[Campaign], *, page: int) -> InlineKeyboardMarkup:
    per_page = CAMPAIGNS_PER_PAGE
    total_pages = max(1, math.ceil(len(campaigns) / per_page))
    page = min(page, total_pages - 1)
    start = page * per_page
    chunk = campaigns[start : start + per_page]
    rows: list[list[InlineKeyboardButton]] = []
    for item in chunk:
        rows.append(
            [
                InlineKeyboardButton(text=f"#{item.id} {item.name[:22]}", callback_data=f"cmp:open:{item.id}"),
            ]
        )
    pager = _paginate_row("cmp:list", page, total_pages)
    if pager:
        rows.insert(0, pager)
    rows.append([InlineKeyboardButton(text="📤 Новая рассылка", callback_data="go:campaign")])
    rows.append(nav_row(home=True))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def campaign_detail_keyboard(campaign_id: int, *, list_page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏸", callback_data=f"cmp:pause:{campaign_id}"),
                InlineKeyboardButton(text="▶️", callback_data=f"cmp:resume:{campaign_id}"),
                InlineKeyboardButton(text="⏹", callback_data=f"cmp:stop:{campaign_id}"),
            ],
            [InlineKeyboardButton(text="📊 Отчёт", callback_data=f"cmp:report:{campaign_id}")],
            nav_row(back=f"cmp:list:p:{list_page}", home=True),
        ]
    )
