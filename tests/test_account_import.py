import pytest

from app.services.account_import_service import AccountImportError, AccountImportService


def test_normalize_session_name() -> None:
    assert AccountImportService.normalize_session_name("acc1") == "acc1"
    assert AccountImportService.normalize_session_name("acc1.session") == "acc1"


def test_normalize_session_name_rejects_invalid() -> None:
    with pytest.raises(AccountImportError):
        AccountImportService.normalize_session_name("1bad")
