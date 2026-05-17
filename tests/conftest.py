from unittest.mock import AsyncMock

import pytest

from app.infrastructure.telethon_clients.sender_adapter import TelethonSenderAdapter
from app.services.compliance_guard import ComplianceGuard
from app.services.sender_service import SenderService


@pytest.fixture
def mock_telethon_adapter() -> TelethonSenderAdapter:
    adapter = AsyncMock(spec=TelethonSenderAdapter)
    adapter.send_group_message = AsyncMock()
    adapter.disconnect_all = AsyncMock()
    adapter.normalize_error = TelethonSenderAdapter.normalize_error
    return adapter


@pytest.fixture
def sender_service(mock_telethon_adapter: TelethonSenderAdapter) -> SenderService:
    return SenderService(guard=ComplianceGuard(), telethon_adapter=mock_telethon_adapter)
