from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SendAttempt


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_campaign_summary(self, campaign_id: int) -> dict:
        result = await self.session.execute(
            select(SendAttempt).where(SendAttempt.campaign_id == campaign_id)
        )
        attempts = list(result.scalars().all())
        statuses = Counter(item.status for item in attempts)
        reasons = Counter(item.error_code or "none" for item in attempts if item.status != "sent_ok")
        return {
            "total_targets": len(attempts),
            "sent_ok": statuses.get("sent_ok", 0),
            "failed": statuses.get("failed", 0),
            "skipped": statuses.get("skipped", 0),
            "floodwait_incidents": reasons.get("floodwait", 0),
            "skip_reasons": dict(reasons),
        }

    async def export_csv(self, campaign_id: int, output_dir: str = "./reports") -> Path:
        result = await self.session.execute(
            select(SendAttempt).where(SendAttempt.campaign_id == campaign_id)
        )
        attempts = list(result.scalars().all())
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"campaign_{campaign_id}.csv"
        with file_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["attempt_id", "account_id", "chat_id", "step_no", "status", "error_code"])
            for item in attempts:
                writer.writerow([item.id, item.account_id, item.chat_id, item.step_no, item.status, item.error_code])
        return file_path
