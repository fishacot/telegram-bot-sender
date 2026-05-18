from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states.campaign_states import CampaignWizardState
from app.config import get_settings
from app.container import get_container
from app.infrastructure.ai_provider.stub_provider import StubAiProvider
from app.infrastructure.db.models import Chat
from app.infrastructure.db.session import SessionLocal
from app.services.ai_assistant_service import AiAssistantService
from app.services.audit_service import AuditService
from app.services.campaign_service import CampaignService
from app.services.compliance_guard import ComplianceError

router = Router()


def _campaign_service(session, sender_service, guard) -> CampaignService:
    return CampaignService(session, guard, sender_service)


@router.message(Command("campaigns"))
async def campaigns_list_handler(message: Message) -> None:
    container = get_container()
    async with SessionLocal() as session:
        service = _campaign_service(session, container.sender_service, container.guard)
        campaigns = await service.list_campaigns()
    if not campaigns:
        await message.answer("No campaigns yet.")
        return
    lines = [f"#{item.id} {item.name} [{item.mode}] -> {item.status}" for item in campaigns[:15]]
    await message.answer(
        "Campaigns:\n" + "\n".join(lines) + "\n\nControls:\n"
        "/campaign_pause <id>\n/campaign_resume <id>\n/campaign_stop <id>"
    )


@router.message(Command("campaign_new"))
async def campaign_new_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CampaignWizardState.pick_accounts)
    await message.answer("Step 1/6: PACK:1,2 (pack ids) or MANUAL:10,11 (account ids)")


@router.message(CampaignWizardState.pick_accounts)
async def campaign_pick_accounts(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if ":" not in raw:
        await message.answer("Use PACK:ids or MANUAL:ids")
        return
    mode_raw, ids_raw = raw.split(":", maxsplit=1)
    mode = mode_raw.strip().lower()
    if mode not in {"pack", "manual"}:
        await message.answer("Mode must be PACK or MANUAL.")
        return
    ids = [int(item.strip()) for item in ids_raw.split(",") if item.strip().isdigit()]
    if not ids:
        await message.answer("Provide numeric ids.")
        return
    if mode == "pack":
        await state.update_data(account_mode="pack", pack_ids=ids)
    else:
        await state.update_data(account_mode="manual", account_ids=ids)
    await state.set_state(CampaignWizardState.pick_chats)
    await message.answer("Step 2/6: chat ids (comma-separated, from /chats).")


@router.message(CampaignWizardState.pick_chats)
async def campaign_pick_chats(message: Message, state: FSMContext) -> None:
    chat_ids = [int(item.strip()) for item in (message.text or "").split(",") if item.strip().isdigit()]
    if not chat_ids:
        await message.answer("Provide numeric chat ids.")
        return
    await state.update_data(chat_ids=chat_ids)
    await state.set_state(CampaignWizardState.pick_template)
    await message.answer("Step 3/6: template id (see /templates).")


@router.message(CampaignWizardState.pick_template)
async def campaign_pick_template(message: Message, state: FSMContext) -> None:
    if not (message.text and message.text.isdigit()):
        await message.answer("Template id must be numeric.")
        return
    await state.update_data(template_id=int(message.text))
    await state.set_state(CampaignWizardState.pick_settings)
    await message.answer(
        "Step 4/6: min_delay,max_delay,max_per_acc_hour,mode\n"
        "Modes: single | rotate | team_dialogue | scheduled_once\n"
        "Example: 15,30,20,single\n"
        "Schedule example: 15,30,20,scheduled_once,2026-05-17T20:00"
    )


@router.message(CampaignWizardState.pick_settings)
async def campaign_pick_settings(message: Message, state: FSMContext) -> None:
    raw = [part.strip() for part in (message.text or "").split(",") if part.strip()]
    if len(raw) < 4:
        await message.answer("Use: min_delay,max_delay,max_per_acc_hour,mode[,scheduled_datetime]")
        return
    try:
        min_delay, max_delay, max_per_acc = int(raw[0]), int(raw[1]), int(raw[2])
    except ValueError:
        await message.answer("Delay and max_per_acc_hour must be integers.")
        return
    campaign_mode = raw[3].lower()
    if campaign_mode not in {"single", "rotate", "team_dialogue", "scheduled_once"}:
        await message.answer("Mode must be: single, rotate, team_dialogue, scheduled_once")
        return
    scheduled_at = None
    if campaign_mode == "scheduled_once":
        if len(raw) < 5:
            await message.answer("For scheduled_once add datetime: ...,scheduled_once,YYYY-MM-DDTHH:MM")
            return
        from datetime import datetime

        scheduled_at = datetime.fromisoformat(raw[4])
        if scheduled_at <= datetime.utcnow():
            await message.answer("Scheduled time must be in the future.")
            return
    settings = {
        "min_delay_msg": min_delay,
        "max_delay_msg": max_delay,
        "min_delay_chat": 30,
        "max_delay_chat": 90,
        "active_hours": "0-23",
        "max_per_acc_hour": max_per_acc,
        "max_per_chat_day": 3,
        "cooldown_hours": 24,
        "jitter_percent": 20,
        "retry_count": 2,
        "retry_backoff_sec": 30,
    }
    container = get_container()
    try:
        container.guard.validate_campaign_limits(settings)
    except ComplianceError as error:
        await message.answer(f"Settings rejected: {error}")
        return

    data = await state.get_data()
    selected = data["chat_ids"]
    allowed: list[int] = []
    excluded: list[str] = []
    async with SessionLocal() as session:
        for chat_id in selected:
            chat = await session.get(Chat, chat_id)
            if not chat:
                excluded.append(f"{chat_id}:not_found")
                continue
            try:
                container.guard.validate_send_permissions(chat.can_send, chat.type)
                if chat.is_blacklisted or chat.is_archived:
                    raise ComplianceError("chat_archived_or_blacklisted")
                allowed.append(chat_id)
            except ComplianceError as error:
                excluded.append(f"{chat_id}:{error}")

        ai = AiAssistantService(session, StubAiProvider(), get_settings().ai_mode_enum)
        ai_hint = await ai.preflight_assistant(
            campaign_id=None,
            context={"settings": settings, "allowed": len(allowed), "excluded": len(excluded)},
        )

    await state.update_data(
        settings=settings,
        allowed_chat_ids=allowed,
        excluded_chats=excluded,
        campaign_mode=campaign_mode,
        scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
    )
    await state.set_state(CampaignWizardState.preflight)
    await message.answer(
        "Step 5/6 Preflight\n"
        f"Selected: {len(selected)} | Allowed: {len(allowed)} | Excluded: {len(excluded)}\n"
        f"Reasons: {', '.join(excluded) if excluded else 'none'}\n"
        f"AI risk: {ai_hint.get('risk')} ({'; '.join(ai_hint.get('reasons', []))})\n"
        "Type CONTINUE for confirmation step."
    )


@router.message(CampaignWizardState.preflight, F.text.casefold() == "continue")
async def campaign_preflight_continue(message: Message, state: FSMContext) -> None:
    await state.set_state(CampaignWizardState.confirm)
    await message.answer("Step 6/6: type CONFIRM to launch or CANCEL to abort.")


@router.message(CampaignWizardState.confirm, F.text.casefold() == "confirm")
async def campaign_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("allowed_chat_ids"):
        await state.clear()
        await message.answer("Blocked: no compliant chats after preflight.")
        return
    actor_id = message.from_user.id if message.from_user else 0
    container = get_container()
    try:
        async with SessionLocal() as session:
            service = _campaign_service(session, container.sender_service, container.guard)
            account_ids = await service.resolve_account_ids(
                data.get("account_mode", "manual"),
                data.get("account_ids", []),
                data.get("pack_ids", []),
            )
            mode = data.get("campaign_mode", "single")
            scheduled_at_raw = data.get("scheduled_at")
            scheduled_at = None
            if scheduled_at_raw:
                from datetime import datetime

                scheduled_at = datetime.fromisoformat(scheduled_at_raw)
            campaign = await service.create_campaign(
                name=f"Campaign {actor_id}-{message.message_id}",
                mode=mode,
                template_id=data["template_id"],
                created_by=actor_id,
                account_ids=account_ids,
                chat_ids=data["allowed_chat_ids"],
                settings=data["settings"],
                scheduled_at=scheduled_at,
            )
            audit = AuditService(session)
            if mode == "scheduled_once":
                if not scheduled_at:
                    await message.answer("scheduled_once requires datetime in step 4.")
                    return
                container.campaign_scheduler.schedule_campaign_run(campaign.id, scheduled_at)
                await audit.log(
                    actor_id,
                    "campaign.schedule",
                    {"campaign_id": campaign.id, "scheduled_at": str(scheduled_at)},
                )
                queued = 0
            else:
                queued = await service.run_campaign(campaign.id, confirmed=True)
                await audit.log(actor_id, "campaign.run", {"campaign_id": campaign.id, "queued": queued})
    except (ComplianceError, ValueError) as error:
        await message.answer(f"Campaign failed: {error}")
        return

    await state.clear()
    if data.get("campaign_mode") == "scheduled_once":
        await message.answer(
            f"Campaign #{campaign.id} scheduled for {scheduled_at}.\nMonitor: /campaigns"
        )
    else:
        await message.answer(
            f"Campaign #{campaign.id} started. Queued messages: {queued}.\n"
            "Monitor: /campaigns | Report: /report <id>"
        )


@router.message(CampaignWizardState.confirm, F.text.casefold() == "cancel")
async def campaign_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Campaign creation cancelled.")


@router.message(Command("campaign_pause"))
async def campaign_pause_handler(message: Message) -> None:
    campaign_id = _parse_campaign_id(message)
    if campaign_id is None:
        await message.answer("Usage: /campaign_pause <campaign_id>")
        return
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0
    async with SessionLocal() as session:
        service = _campaign_service(session, container.sender_service, container.guard)
        await service.pause(campaign_id)
        await AuditService(session).log(actor_id, "campaign.pause", {"campaign_id": campaign_id})
    await message.answer(f"Campaign #{campaign_id} paused.")


@router.message(Command("campaign_resume"))
async def campaign_resume_handler(message: Message) -> None:
    campaign_id = _parse_campaign_id(message)
    if campaign_id is None:
        await message.answer("Usage: /campaign_resume <campaign_id>")
        return
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0
    async with SessionLocal() as session:
        service = _campaign_service(session, container.sender_service, container.guard)
        await service.resume(campaign_id)
        await AuditService(session).log(actor_id, "campaign.resume", {"campaign_id": campaign_id})
    await message.answer(f"Campaign #{campaign_id} resumed.")


@router.message(Command("campaign_stop"))
async def campaign_stop_handler(message: Message) -> None:
    campaign_id = _parse_campaign_id(message)
    if campaign_id is None:
        await message.answer("Usage: /campaign_stop <campaign_id>")
        return
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0
    async with SessionLocal() as session:
        service = _campaign_service(session, container.sender_service, container.guard)
        await service.stop(campaign_id)
        await AuditService(session).log(actor_id, "campaign.stop", {"campaign_id": campaign_id})
    await message.answer(f"Campaign #{campaign_id} stopped.")


def _parse_campaign_id(message: Message) -> int | None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return int(parts[1])
