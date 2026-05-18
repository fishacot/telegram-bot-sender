from app.bot.texts.errors_ru import humanize_error
from app.services.compliance_guard import ComplianceError


def test_humanize_active_hours():
    text = humanize_error(ComplianceError("Outside configured active hours."))
    assert "часов" in text.lower()


def test_humanize_passthrough():
    assert humanize_error("Custom short error") == "Custom short error"
