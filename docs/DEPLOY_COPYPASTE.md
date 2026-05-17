# Деплой — копируй и вставляй (Railway, дёшево)

Выбран **Railway без PostgreSQL** — один сервис, SQLite на диске. Так дольше хватает баланса ($4+).

---

## Шаг 1. Railway — новый проект

1. Откройте [railway.app](https://railway.app) → войдите через GitHub.
2. **New Project** → **Deploy from GitHub repo**.
3. Выберите: **`fishacot/telegram-bot-sender`**.
4. **PostgreSQL НЕ добавляйте** (не нажимайте Provision Database).

Подождите 2–3 минуты, пока идёт Build.

---

## Шаг 2. Volume (диск для сессий и базы)

1. Кликните на **сервис с ботом** (не на Postgres, если случайно создали — удалите Postgres).
2. Вкладка **Volumes** → **Add Volume**.
3. **Mount path:** `/data`
4. Save.

---

## Шаг 3. Variables — вставьте целиком

Сервис бота → **Variables** → **RAW Editor** (или по одной).

Скопируйте и **замените только BOT_TOKEN** на свой от BotFather:

```env
BOT_TOKEN=ВСТАВЬТЕ_ТОКЕН_ОТ_BOTFATHER
ADMIN_IDS=8760867989
TELEGRAM_API_ID=2040
TELEGRAM_API_HASH=b18441a1ff607e10a989891a5462e627
DATABASE_URL=sqlite+aiosqlite:////data/app.db
SESSIONS_DIR=/data/sessions
LOG_LEVEL=INFO
LOG_JSON=true
```

**Не добавляйте** `DATABASE_URL` из PostgreSQL.

Нажмите **Deploy** / дождитесь перезапуска.

---

## Шаг 4. Проверка логов

**Deployments** → **View Logs**.

Должно быть:

```text
Run polling for bot @...
```

---

## Шаг 5. Telegram — первый запуск

1. Откройте бота → `/start`
2. **👤 Аккаунты** → **➕ Загрузить .session** → отправьте файл `.session`
3. **💬 Чаты** → **➕ Добавить чат** → ссылка на группу
4. **📝 Шаблоны** → **➕ Новый шаблон**
5. **📤 Новая рассылка** → **🚀 Запустить**

---

## Session-файл на ПК (один раз)

С VPN на компьютере:

```powershell
cd "c:\Users\user\Desktop\телеграм рассылка"
.\.venv\Scripts\Activate.ps1
python scripts/auth_session.py --name acc1
```

Файл: `sessions\acc1.session` → отправьте боту.

---

## Если бот не отвечает

| Проблема | Решение |
|----------|---------|
| Нет `Run polling` в логах | Проверьте `BOT_TOKEN` и Redeploy |
| Бот молчит | `ADMIN_IDS=8760867989` |
| Session not authorized | Загрузите `.session` снова в бота |

---

## Обновление кода

В Cursor: **Commit** → **Sync**. Railway пересоберёт сам.
