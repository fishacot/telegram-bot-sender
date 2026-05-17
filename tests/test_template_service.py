from app.services.compliance_guard import ComplianceGuard
from app.services.template_service import TemplateService


def test_template_rendering() -> None:
    service = TemplateService(ComplianceGuard())
    rendered = service.render_preview(
        "Hello from {shop} in {city}. Link: {link}",
        {"shop": "StoreX", "city": "Berlin", "link": "https://example.com"},
    )
    assert "StoreX" in rendered
    assert "Berlin" in rendered
