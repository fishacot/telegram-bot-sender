# Конфигурация Cursor в этом репозитории

Краткий индекс. Полный контракт — в **`../AGENTS.md`**.

## Rules (`.cursor/rules/`)

| Файл | `alwaysApply` / `globs` | Назначение |
|------|-------------------------|------------|
| `agent-workflow-core.mdc` | `true` | План → diff → `AGENTS` Verification → `npm run verify` при правках md/mdc. |
| `security-trust.mdc` | `true` | Секреты, не коммитить ключи, плейсхолдеры. |
| `task-closure-protocol.mdc` | `true` | Шаблон задачи, приёмка, до 3 циклов verify, явное «да» на риски. |
| `markdown-prompts.mdc` | `globs: **/*.md` | Промпты и документация в Markdown. |
| `cursor-mdc-authoring.mdc` | `.cursor/rules/**/*.mdc` | Оформление `.mdc`. |
| `package-json-ci.mdc` | `package.json` | Скрипты и зависимости. |
| `github-actions.mdc` | `.github/workflows/*.yml` | Минимальные workflow. |
| `dependabot-config.mdc` | `.github/dependabot.yml` | Расписание и лимиты Dependabot. |

## Commands (`.cursor/commands/`)

| Файл | Назначение |
|------|------------|
| `agent-preflight.md` | Перед правками. |
| `agent-plan-deep.md` | Глубокий план без правок. |
| `agent-verify.md` | `npm run verify`. |
| `agent-postflight.md` | Итог и повторная проверка. |
| `agent-task-intake.md` | Структурировать запрос по `docs/TASK_TEMPLATE.md`. |
| `agent-confirm-acceptance.md` | Подтверждение приёмки и рисков. |

Подключение в UI: см. **`../docs/CURSOR_SETUP.md`**.
