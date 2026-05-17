# Подсказка по деплою (не деплоит сам — нужен ваш Railway аккаунт)
Write-Host "=== Railway deploy checklist ===" -ForegroundColor Cyan
Write-Host "1) python scripts/auth_session.py --name acc1"
Write-Host "2) git push to GitHub"
Write-Host "3) railway.app -> New Project -> GitHub repo"
Write-Host "4) Add PostgreSQL, link DATABASE_URL"
Write-Host "5) Set BOT_TOKEN, ADMIN_IDS, SESSIONS_DIR=/data/sessions"
Write-Host "6) Add Volume mount /data, upload sessions/acc1.session"
Write-Host "7) Deploy -> check logs for 'Run polling'"
Write-Host ""
Write-Host "Full guide: docs/DEPLOY_RAILWAY.md"
