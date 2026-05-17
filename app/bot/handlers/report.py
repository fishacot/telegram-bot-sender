from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from app.infrastructure.db.session import SessionLocal
from app.services.report_service import ReportService

router = Router()


@router.message(Command("report"))
async def report_handler(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /report <campaign_id>")
        return
    campaign_id = int(parts[1])
    async with SessionLocal() as session:
        service = ReportService(session)
        summary = await service.build_campaign_summary(campaign_id)
        csv_path = await service.export_csv(campaign_id)
    await message.answer(
        "Report summary:\n"
        f"- total targets: {summary['total_targets']}\n"
        f"- sent_ok: {summary['sent_ok']}\n"
        f"- failed: {summary['failed']}\n"
        f"- skipped: {summary['skipped']}\n"
        f"- floodwait incidents: {summary['floodwait_incidents']}\n"
        f"- skip reasons: {summary['skip_reasons']}"
    )
    await message.answer_document(FSInputFile(csv_path))
