from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.proxy_url import (
    BulkProxyAssignResult,
    ProxyParseError,
    mask_proxy_url,
    parse_proxy_bulk_text,
    parse_proxy_line,
)
from app.infrastructure.db.models import Account
from app.infrastructure.telethon_clients.factory import TelethonClientFactory


class AccountProxyService:
    def __init__(self, session: AsyncSession, factory: TelethonClientFactory) -> None:
        self.session = session
        self.factory = factory

    @staticmethod
    def parse_proxy_input(raw: str) -> str | None:
        text = (raw or "").strip()
        if not text or text.lower() in {"off", "none", "нет", "-", "remove", "удалить"}:
            return None
        return parse_proxy_line(text)

    async def list_active_accounts(self) -> list[Account]:
        result = await self.session.execute(
            select(Account).where(Account.is_active.is_(True)).order_by(Account.id)
        )
        return list(result.scalars().all())

    def _validate_stored_proxy(self, proxy_value: str | None) -> None:
        if proxy_value:
            self.factory.validate_proxy(proxy_value)

    async def set_account_proxy(self, account_id: int, raw: str) -> Account:
        proxy_value = self.parse_proxy_input(raw)
        self._validate_stored_proxy(proxy_value)

        account = await self.session.get(Account, account_id)
        if not account:
            raise ValueError("Аккаунт не найден.")
        account.proxy = proxy_value
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def bulk_assign_round_robin(self, text: str) -> BulkProxyAssignResult:
        """Несколько прокси по кругу: acc[i] получает proxy[i % len(proxies)]."""
        proxy_lines = parse_proxy_bulk_text(text)
        accounts = await self.list_active_accounts()
        if not accounts:
            raise ValueError("Нет активных аккаунтов. Сначала загрузите .session.")
        if not proxy_lines:
            raise ValueError("Добавьте хотя бы одну строку с прокси.")

        parsed_proxies: list[str] = []
        errors: list[str] = []
        for index, proxy_raw in enumerate(proxy_lines):
            try:
                proxy_value = self.parse_proxy_input(proxy_raw)
                self._validate_stored_proxy(proxy_value)
                parsed_proxies.append(proxy_value or "")
            except ProxyParseError as exc:
                errors.append(f"Строка {index + 1}: {exc}")

        if not parsed_proxies:
            raise ProxyParseError("Нет валидных прокси в списке.")

        updated: list[tuple[int, str, str]] = []
        for index, account in enumerate(accounts):
            proxy_value = parsed_proxies[index % len(parsed_proxies)]
            account.proxy = proxy_value or None
            updated.append((account.id, account.name, mask_proxy_url(proxy_value)))

        await self.session.commit()
        return BulkProxyAssignResult(updated=updated, unchanged_account_names=[], errors=errors)

    async def bulk_assign_by_order(self, text: str) -> BulkProxyAssignResult:
        proxy_lines = parse_proxy_bulk_text(text)
        accounts = await self.list_active_accounts()
        if not accounts:
            raise ValueError("Нет активных аккаунтов. Сначала загрузите .session.")

        updated: list[tuple[int, str, str]] = []
        errors: list[str] = []

        for index, proxy_raw in enumerate(proxy_lines):
            if index >= len(accounts):
                errors.append(
                    f"Строка {index + 1}: лишняя (аккаунтов только {len(accounts)})."
                )
                continue
            account = accounts[index]
            try:
                proxy_value = self.parse_proxy_input(proxy_raw)
                self._validate_stored_proxy(proxy_value)
                account.proxy = proxy_value
                updated.append((account.id, account.name, mask_proxy_url(proxy_value)))
            except ProxyParseError as exc:
                errors.append(f"Строка {index + 1}: {exc}")

        unchanged = [a.name for a in accounts[len(proxy_lines) :]]

        if updated:
            await self.session.commit()
        return BulkProxyAssignResult(updated=updated, unchanged_account_names=unchanged, errors=errors)

    async def apply_proxy_to_all(self, raw: str) -> BulkProxyAssignResult:
        proxy_value = self.parse_proxy_input(raw)
        self._validate_stored_proxy(proxy_value)
        accounts = await self.list_active_accounts()
        if not accounts:
            raise ValueError("Нет активных аккаунтов.")

        updated: list[tuple[int, str, str]] = []
        masked = mask_proxy_url(proxy_value)
        for account in accounts:
            account.proxy = proxy_value
            updated.append((account.id, account.name, masked))
        await self.session.commit()
        return BulkProxyAssignResult(updated=updated, unchanged_account_names=[], errors=[])
