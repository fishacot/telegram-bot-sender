# Деплой на Railway

Сам я за вас в Railway зайти не могу — нужен ваш аккаунт. Ниже пошагово (15–20 мин).

## Что получится

- Бот работает **24/7** на сервере Railway (обычно без VPN с ПК).
- БД: **PostgreSQL** (добавить в проект Railway).
- Telethon-сессии: **Volume** `/data/sessions` (файлы загружаете один раз).

## 1. Подготовка на ПК

### Session (обязательно до деплоя)

```powershell
cd "c:\Users\user\Desktop\телеграм рассылка"
.\.venv\Scripts\Activate.ps1
python scripts/auth_session.py --name acc1
```

Появится `sessions\acc1.session` — этот файл нужен на сервере.

### GitHub (если ещё нет репозитория)

```powershell
git init
git add .
git commit -m "railway deploy"
# создайте репо на GitHub и:
git remote add origin https://github.com/ВАШ_ЛОГИН/telegram-broadcast.git
git push -u origin main
```

## 2. Проект в Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Выберите репозиторий с этим проектом.
3. **+ New** → **Database** → **PostgreSQL**.
4. В сервисе бота → **Variables** → **Add Reference** → `DATABASE_URL` из Postgres.

### Переменные (Variables) для бота

| Variable | Значение |
|----------|----------|
| `BOT_TOKEN` | токен от BotFather |
| `ADMIN_IDS` | `8760867989` (ваш id) |
| `TELEGRAM_API_ID` | `2040` |
| `TELEGRAM_API_HASH` | ваш hash |
| `DATABASE_URL` | reference из PostgreSQL |
| `SESSIONS_DIR` | `/data/sessions` |

`TELEGRAM_PROXY` на Railway обычно **не нужен**.

## 3. Session-аккаунт (через бота)

После деплоя в Telegram у бота:

```text
/account_upload acc1 lead
```

Отправьте файл `acc1.session` (созданный локально через `python scripts/auth_session.py --name acc1`).

Аккаунт попадёт в пул автоматически. Volume `/data` + `SESSIONS_DIR=/data/sessions` сохранит файл на сервере.

## 4. Деплой

Railway подхватит `Dockerfile` и `railway.toml`. Старт: миграции + `python -m app.main`.

Логи: сервис → **Deployments** → **View Logs**. Должно быть:

```text
Run polling for bot @...
```

## 5. Первый запуск в боте (кнопки меню)

В Telegram у вашего бота:

1. `/start`
2. **👤 Аккаунты** → **➕ Загрузить .session** → файл `acc1.session`
3. **💬 Чаты** → **➕ Добавить чат** → ссылка на группу
4. **📝 Шаблоны** → **➕ Новый шаблон**
5. **📤 Новая рассылка** → кнопки до **🚀 Запустить**

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| `Session not authorized` | Нет `acc1.session` в `/data/sessions` |
| Бот не отвечает | Проверьте `ADMIN_IDS` и логи Railway |
| Ошибка БД | `DATABASE_URL` привязан к Postgres, redeploy |
| Локально timeout | Деплой на Railway — обход блокировки с ПК |

## Обновление

```powershell
git add .
git commit -m "update"
git push
```

Railway пересоберёт контейнер автоматически.
