# Бесплатный деплой на Render (без оплаты)

Railway на trial **рано или поздно остановится**.  
**Render Free** — $0, для нашего бота подходит.

> После каждого **полного** передеплоя может сброситься база на диске контейнера.  
> Файл `.session` просто **загрузите в бота снова** (кнопка 👤 Аккаунты).

---

## 1. Регистрация

1. [render.com](https://render.com) → **Get Started** → войти через **GitHub** (`fishacot`).

---

## 2. Новый Web Service

1. **Dashboard** → **New +** → **Web Service**.
2. Connect repository: **`fishacot/telegram-bot-sender`**.
3. Настройки:

| Поле | Значение |
|------|----------|
| Name | `telegram-bot-sender` |
| Region | Frankfurt (или ближайший) |
| Branch | `main` |
| Runtime | **Docker** |
| Instance Type | **Free** |

4. **Advanced** → Health Check Path: `/`

---

## 3. Environment Variables

Вкладка **Environment** → **Add from .env** или вставьте построчно.

**Скопируйте весь файл** `render.env.local` из корня проекта на ПК  
(файл **не в GitHub** — там уже ваши данные):

```
c:\Users\user\Desktop\телеграм рассылка\render.env.local
```

Откройте в блокноте → Ctrl+A → Ctrl+C → вставьте в Render.

**PostgreSQL не нужен.** Для сохранения БД между рестартами контейнера добавьте в Environment:

```env
DATABASE_URL=sqlite+aiosqlite:////data/app.db
SESSIONS_DIR=/data/sessions
```

Шаблон всех переменных: `render.env.example` в корне проекта.

---

## 4. Create Web Service

Нажмите **Create Web Service**. Ждите **Live** (5–10 мин).

**Logs** → должно быть:

```text
Run polling for bot @...
```

---

## 5. Telegram

`/start` → дальше только кнопки меню.

Session на ПК (с VPN):

```powershell
cd "c:\Users\user\Desktop\телеграм рассылка"
.\.venv\Scripts\Activate.ps1
python scripts/auth_session.py --name acc1
```

Файл `sessions\acc1.session` → в боте **👤 Аккаунты** → **➕ Загрузить .session**.

---

## Обновление кода

Cursor → **Commit** → **Sync** → Render пересоберёт сам.

---

## Если Render «засыпает»

На Free иногда сервис спит. Напишите боту `/start` — обычно просыпается за 30–60 сек.

Если не помогает — напишите, настроим **Fly.io** (тоже бесплатный лимит).
