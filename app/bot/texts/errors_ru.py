"""Понятные сообщения об ошибках для пользователя бота."""

from __future__ import annotations

_ERROR_MAP: dict[str, str] = {
    "outside configured active hours.": "Сейчас вне разрешённых часов отправки. Подождите или смените настройки.",
    "no permission to send in selected chat.": "В этот чат нельзя писать с выбранного аккаунта.",
    "sending to private/user dialogs is forbidden.": "Личные диалоги запрещены — только группы и каналы.",
    "chat_archived_or_blacklisted": "Чат в архиве или в чёрном списке.",
    "archived": "Чат в архиве.",
    "explicit confirmation is required before run.": "Нужно подтверждение запуска.",
    "campaign has no target chats.": "Нет чатов для рассылки.",
    "campaign has no sender accounts.": "Нет аккаунта-отправителя.",
    "account or chat not found.": "Аккаунт или чат не найден в базе.",
    "template not found or inactive.": "Шаблон не найден или отключён.",
    "max_per_acc_hour limit reached.": "Лимит сообщений в час для аккаунта исчерпан. Подождите.",
    "max_per_chat_day limit reached.": "Лимит сообщений в этот чат на сегодня исчерпан.",
    "not authorized": "Сессия не авторизована. Перезагрузите .session с тем же API ID.",
}


def humanize_error(error: BaseException | str) -> str:
    raw = str(error).strip()
    if not raw:
        return "Неизвестная ошибка."
    lowered = raw.lower()
    for key, message in _ERROR_MAP.items():
        if key in lowered:
            return message
    if "floodwait" in lowered:
        return f"Telegram просит подождать (FloodWait). {raw}"
    if "proxy" in lowered or "connection" in lowered:
        return f"Проблема сети или прокси. Проверьте 🌐 Прокси у аккаунта.\n<code>{raw[:200]}</code>"
    if len(raw) > 280:
        return raw[:280] + "…"
    return raw
