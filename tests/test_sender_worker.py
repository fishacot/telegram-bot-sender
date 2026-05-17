import pytest

from app.services.sender_service import SendTask


@pytest.mark.asyncio
async def test_sender_worker_completes_campaign(sender_service, monkeypatch) -> None:
    completed: list[int] = []

    async def fake_process(task: SendTask) -> None:
        await sender_service._sleep_with_jitter({"min_delay_msg": 0, "max_delay_msg": 0, "jitter_percent": 0})

    async def fake_save(task: SendTask, status: str, error_code: str | None, error_text: str | None) -> None:
        _ = (task, status, error_code, error_text)

    async def on_complete(campaign_id: int) -> None:
        completed.append(campaign_id)

    monkeypatch.setattr(sender_service, "_process_task", fake_process)
    monkeypatch.setattr(sender_service, "_save_attempt", fake_save)
    sender_service.set_campaign_complete_handler(on_complete)
    sender_service.register_campaign_settings(1, {"min_delay_msg": 0, "max_delay_msg": 0, "jitter_percent": 0})

    await sender_service.start_background_worker()
    await sender_service.enqueue(
        SendTask(campaign_id=1, account_id=1, chat_id=1, text="safe group message", step_no=1)
    )
    await sender_service.queue.join()
    await sender_service.stop_background_worker()
    assert completed == [1]
