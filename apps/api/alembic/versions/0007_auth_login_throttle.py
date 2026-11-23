"""Add persistent login attempt throttling.

Revision ID: 0007_auth_login_throttle
Revises: 0006_organization_invitations
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_auth_login_throttle"
down_revision = "0006_organization_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_login_throttles",
        sa.Column("bucket_key", sa.String(length=64), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("bucket_key"),
    )
    op.create_index("ix_auth_login_throttles_window", "auth_login_throttles", ["window_started_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_login_throttles_window", table_name="auth_login_throttles")
    op.drop_table("auth_login_throttles")
