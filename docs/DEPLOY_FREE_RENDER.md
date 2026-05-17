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

Вкладка **Environment** → Add Environment Variable (или Bulk):

```env
BOT_TOKEN=ВСТАВЬТЕ_ТОКЕН_ОТ_BOTFATHER
ADMIN_IDS=8760867989
TELEGRAM_API_ID=2040
TELEGRAM_API_HASH=b18441a1ff607e10a989891a5462e627
DATABASE_URL=sqlite+aiosqlite:///./app.db
SESSIONS_DIR=./sessions
LOG_LEVEL=INFO
LOG_JSON=true
```

**PostgreSQL не нужен.**

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
