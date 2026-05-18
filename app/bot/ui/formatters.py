from __future__ import annotations

from dataclasses import dataclass

from app.domain.proxy_url import mask_proxy_url
from app.infrastructure.db.models import Account, Campaign, Chat, Template


@dataclass(frozen=True)
class SetupStatus:
    accounts: int
    chats: int
    templates: int
    running_campaigns: int

    @property
    def ready_steps(self) -> int:
        return sum([self.accounts > 0, self.chats > 0, self.templates > 0])

    @property
    def is_ready(self) -> bool:
        return self.ready_steps == 3

    def missing_labels(self) -> list[str]:
        missing: list[str] = []
        if self.accounts <= 0:
            missing.append("аккаунты")
        if self.chats <= 0:
            missing.append("чаты")
        if self.templates <= 0:
            missing.append("шаблоны")
        return missing


def build_setup_status(
    accounts: list[Account],
    chats: list[Chat],
    templates: list[Template],
    campaigns: list[Campaign],
) -> SetupStatus:
    running = sum(1 for c in campaigns if c.status in {"running", "queued", "paused"})
    return SetupStatus(
        accounts=len(accounts),
        chats=len(chats),
        templates=len(templates),
        running_campaigns=running,
    )


def format_dashboard(status: SetupStatus, *, steps_text: str = "") -> str:
    if status.is_ready:
        readiness = "✅ Готово к запуску — нажмите <b>📤 Новая рассылка</b>"
        tail = ""
    else:
        missing = ", ".join(status.missing_labels())
        readiness = f"⏳ Не хватает: {missing}"
        tail = f"\n\n{steps_text}" if steps_text else ""

    stats = (
        f"Аккаунтов: {status.accounts} · чатов: {status.chats} · шаблонов: {status.templates}"
    )
    if status.running_campaigns:
        stats += f" · в работе: {status.running_campaigns}"

    return (
        "👋 <b>Панель рассылки</b>\n\n"
        f"{readiness}\n"
        f"<i>{stats}</i>"
        f"{tail}"
    )


def wizard_step(step: int, total: int, title: str) -> str:
    bar = "".join("●" if i < step else "○" for i in range(total))
    return f"📤 <b>{title}</b>\n<code>{bar}</code> шаг {step}/{total}"


def format_accounts_section(accounts: list[Account], *, page: int, per_page: int, total_pages: int) -> str:
    if not accounts:
        return "👤 <b>Аккаунты</b>\n\nПока пусто.\nНажмите <b>➕ Загрузить .session</b>."
    start = page * per_page
    chunk = accounts[start : start + per_page]
    lines = []
    for a in chunk:
        proxy_label = mask_proxy_url(a.proxy)
        if not a.proxy:
            proxy_label = "⚠️ нет прокси"
        lines.append(f"#{a.id} <b>{a.name}</b> · {a.role} · 🌐 {proxy_label}")
    header = f"👤 <b>Аккаунты</b> ({len(accounts)}) · стр. {page + 1}/{total_pages}\n\n"
    return header + "\n".join(lines)


def format_chats_section(chats: list[Chat], *, page: int, per_page: int, total_pages: int) -> str:
    if not chats:
        return "💬 <b>Чаты</b>\n\nПока пусто.\nНажмите <b>➕ Добавить чат</b>."
    start = page * per_page
    chunk = chats[start : start + per_page]
    lines = [
        f"#{c.id} {c.title or '—'} · {'✅' if c.can_send else '🚫'}"
        for c in chunk
    ]
    header = f"💬 <b>Чаты</b> ({len(chats)}) · стр. {page + 1}/{total_pages}\n\n"
    return header + "\n".join(lines)


def format_templates_section(templates: list[Template], *, page: int, per_page: int, total_pages: int) -> str:
    if not templates:
        return "📝 <b>Шаблоны</b>\n\nПока пусто.\nНажмите <b>➕ Новый шаблон</b>."
    start = page * per_page
    chunk = templates[start : start + per_page]
    lines = [f"#{t.id} <b>{t.name}</b>" for t in chunk]
    header = f"📝 <b>Шаблоны</b> ({len(templates)}) · стр. {page + 1}/{total_pages}\n\n"
    return header + "\n".join(lines)


def format_campaigns_list(campaigns: list[Campaign], *, page: int, per_page: int, total_pages: int) -> str:
    if not campaigns:
        return "📋 <b>Мои рассылки</b>\n\nПока пусто.\nНажмите <b>📤 Новая рассылка</b>."
    start = page * per_page
    chunk = campaigns[start : start + per_page]
    status_icon = {
        "running": "▶️",
        "queued": "⏳",
        "paused": "⏸",
        "stopped": "⏹",
        "completed": "✅",
        "draft": "📝",
    }
    lines = [
        f"{status_icon.get(c.status, '•')} #{c.id} <b>{c.name}</b> · {c.mode} · {c.status}"
        for c in chunk
    ]
    header = f"📋 <b>Мои рассылки</b> ({len(campaigns)}) · стр. {page + 1}/{total_pages}\n\n"
    return header + "\n".join(lines)


def format_campaign_confirm(
    *,
    account_id: int,
    account_name: str,
    template_id: int,
    template_name: str,
    selected_count: int,
    allowed_count: int,
    excluded_count: int,
    delay_label: str,
    proxy_warning: str = "",
) -> str:
    proxy_line = f"\n{proxy_warning}" if proxy_warning else ""
    return (
        "📋 <b>Проверка перед запуском</b>\n\n"
        f"👤 {account_name} (#{account_id}){proxy_line}\n"
        f"📝 {template_name} (#{template_id})\n"
        f"💬 Выбрано: {selected_count} · можно: <b>{allowed_count}</b>"
        f" · исключено: {excluded_count}\n"
        f"⏱ Задержка: {delay_label}\n\n"
        "Запустить рассылку?"
    )
