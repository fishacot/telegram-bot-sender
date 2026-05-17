from app.bot.ui.formatters import SetupStatus, build_setup_status, format_dashboard, wizard_step
from app.infrastructure.db.models import Account, Campaign, Chat, Template


def test_dashboard_not_ready():
    status = SetupStatus(accounts=1, chats=0, templates=0, running_campaigns=0)
    text = format_dashboard(status)
    assert "1/3" in text
    assert "чаты" in text


def test_dashboard_ready():
    status = SetupStatus(accounts=2, chats=3, templates=1, running_campaigns=0)
    text = format_dashboard(status)
    assert "Готово" in text


def test_wizard_step():
    assert "шаг 2/4" in wizard_step(2, 4, "Тест")


def test_build_setup_status():
    accounts = [Account(name="a", session_path="a", is_active=True)]
    chats = [Chat(tg_chat_id=1, title="t", username="u", type="group", can_send=True)]
    templates = [Template(name="t", kind="text", body="b")]
    campaigns = [Campaign(name="c", mode="single", status="running", template_id=1, created_by=1)]
    status = build_setup_status(accounts, chats, templates, campaigns)
    assert status.is_ready
    assert status.running_campaigns == 1
