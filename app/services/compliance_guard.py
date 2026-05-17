from __future__ import annotations

from dataclasses import dataclass

from app.domain.chat_target import ChatTargetKind, ChatTargetParser, ParsedChatTarget


class ComplianceError(Exception):
    pass


@dataclass(slots=True)
class ComplianceResult:
    allowed: bool
    reason: str | None = None


class ComplianceGuard:
    SAFE_CHAT_TYPES = {"group", "supergroup", "channel"}

    def validate_chat_type(self, chat_type: str) -> ComplianceResult:
        if chat_type not in self.SAFE_CHAT_TYPES:
            raise ComplianceError("Sending to private/user dialogs is forbidden.")
        return ComplianceResult(allowed=True)

    def validate_send_permissions(self, can_send: bool, chat_type: str) -> ComplianceResult:
        self.validate_chat_type(chat_type)
        if not can_send:
            raise ComplianceError("No permission to send in selected chat.")
        return ComplianceResult(allowed=True)

    def validate_campaign_limits(self, settings: dict) -> ComplianceResult:
        min_delay = settings["min_delay_msg"]
        max_delay = settings["max_delay_msg"]
        if min_delay < 5:
            raise ComplianceError("min_delay_msg must be >= 5 seconds.")
        if min_delay > max_delay:
            raise ComplianceError("min_delay_msg cannot exceed max_delay_msg.")
        if settings["max_per_acc_hour"] > 30:
            raise ComplianceError("max_per_acc_hour exceeds safe threshold (30).")
        return ComplianceResult(allowed=True)

    def validate_before_run(self, campaign: dict) -> ComplianceResult:
        if not campaign.get("confirmed"):
            raise ComplianceError("Owner confirmation is required before campaign run.")
        if not campaign.get("account_ids"):
            raise ComplianceError("Campaign has no sender accounts.")
        if not campaign.get("chat_ids"):
            raise ComplianceError("Campaign has no target chats.")
        return ComplianceResult(allowed=True)

    def assert_safe_content(self, text: str) -> ComplianceResult:
        banned_patterns = ["write me in pm", "contact me in private"]
        lowered = text.lower()
        for pattern in banned_patterns:
            if pattern in lowered:
                raise ComplianceError("Template contains disallowed private outreach pattern.")
        return ComplianceResult(allowed=True)

    def parse_join_target(self, raw: str) -> ParsedChatTarget:
        try:
            parsed = ChatTargetParser.parse(raw)
        except ValueError as error:
            raise ComplianceError(str(error)) from error
        if parsed.kind not in {ChatTargetKind.USERNAME, ChatTargetKind.INVITE}:
            raise ComplianceError("Only public username or group invite links are allowed.")
        return parsed

    def validate_join_target(self, raw: str) -> ComplianceResult:
        self.parse_join_target(raw)
        return ComplianceResult(allowed=True)
