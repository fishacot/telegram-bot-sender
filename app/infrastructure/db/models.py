from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    session_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="lead", nullable=False)
    proxy: Mapped[str | None] = mapped_column(String(512), nullable=True)
    health_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AccountPack(Base):
    __tablename__ = "account_packs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)


class AccountPackItem(Base):
    __tablename__ = "account_pack_items"
    pack_id: Mapped[int] = mapped_column(ForeignKey("account_packs.id"), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)


class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    username: Mapped[str | None] = mapped_column(String(256), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    can_send: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    steps: Mapped[list["TeamStep"]] = relationship(back_populates="template")


class TeamStep(Base):
    __tablename__ = "team_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    delay_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_to_prev: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    template: Mapped["Template"] = relationship(back_populates="steps")
    __table_args__ = (UniqueConstraint("template_id", "step_no", name="uq_team_step"),)


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CampaignAccount(Base):
    __tablename__ = "campaign_accounts"
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)


class CampaignChat(Base):
    __tablename__ = "campaign_chats"
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), primary_key=True)


class CampaignSettings(Base):
    __tablename__ = "campaign_settings"
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), primary_key=True)
    min_delay_msg: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    max_delay_msg: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    min_delay_chat: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_delay_chat: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    active_hours: Mapped[str] = mapped_column(String(32), default="0-23", nullable=False)
    max_per_acc_hour: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    max_per_chat_day: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    jitter_percent: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    retry_backoff_sec: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SendAttempt(Base):
    __tablename__ = "send_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False)
    step_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class WarmupRun(Base):
    __tablename__ = "warmup_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class JoinTask(Base):
    __tablename__ = "join_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    chat_username: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AgentErrorEvent(Base):
    __tablename__ = "agent_error_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AiRecommendation(Base):
    __tablename__ = "ai_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
