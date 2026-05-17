"""add scheduled_at to campaign_settings

Revision ID: 20260516_0002
Revises: 20260516_0001
Create Date: 2026-05-16 21:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260516_0002"
down_revision = "20260516_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaign_settings", sa.Column("scheduled_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_settings", "scheduled_at")
