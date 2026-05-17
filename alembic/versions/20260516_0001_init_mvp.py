"""init mvp schema

Revision ID: 20260516_0001
Revises:
Create Date: 2026-05-16 19:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260516_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("session_path", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="lead"),
        sa.Column("proxy", sa.String(length=256), nullable=True),
        sa.Column("health_status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "account_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
    )
    op.create_table(
        "account_pack_items",
        sa.Column("pack_id", sa.Integer(), sa.ForeignKey("account_packs.id"), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), primary_key=True),
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_chat_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("username", sa.String(length=256), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("can_send", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_blacklisted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("variables_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "team_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("templates.id"), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("delay_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reply_to_prev", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("template_id", "step_no", name="uq_team_step"),
    )
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("templates.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "campaign_accounts",
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), primary_key=True),
    )
    op.create_table(
        "campaign_chats",
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id"), primary_key=True),
    )
    op.create_table(
        "campaign_settings",
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), primary_key=True),
        sa.Column("min_delay_msg", sa.Integer(), nullable=False),
        sa.Column("max_delay_msg", sa.Integer(), nullable=False),
        sa.Column("min_delay_chat", sa.Integer(), nullable=False),
        sa.Column("max_delay_chat", sa.Integer(), nullable=False),
        sa.Column("active_hours", sa.String(length=32), nullable=False),
        sa.Column("max_per_acc_hour", sa.Integer(), nullable=False),
        sa.Column("max_per_chat_day", sa.Integer(), nullable=False),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False),
        sa.Column("jitter_percent", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("retry_backoff_sec", sa.Integer(), nullable=False),
    )
    op.create_table(
        "send_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "warmup_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "join_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("chat_username", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "ai_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("ai_recommendations")
    op.drop_table("audit_events")
    op.drop_table("join_tasks")
    op.drop_table("warmup_runs")
    op.drop_table("send_attempts")
    op.drop_table("campaign_settings")
    op.drop_table("campaign_chats")
    op.drop_table("campaign_accounts")
    op.drop_table("campaigns")
    op.drop_table("team_steps")
    op.drop_table("templates")
    op.drop_table("chats")
    op.drop_table("account_pack_items")
    op.drop_table("account_packs")
    op.drop_table("accounts")
