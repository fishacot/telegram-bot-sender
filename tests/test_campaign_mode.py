from app.services.campaign_service import CampaignService


def test_single_mode_uses_first_account() -> None:
    account_ids = [10, 20, 30]
    for idx in range(3):
        assert CampaignService.pick_account_id("single", account_ids, idx) == 10


def test_rotate_mode_cycles_accounts() -> None:
    account_ids = [10, 20, 30]
    assert CampaignService.pick_account_id("rotate", account_ids, 0) == 10
    assert CampaignService.pick_account_id("rotate", account_ids, 1) == 20
    assert CampaignService.pick_account_id("rotate", account_ids, 3) == 10
