"""Add organization-scoped API keys.

Revision ID: 0009_api_keys
Revises: 0008_audit_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_api_keys"
down_revision = "0008_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=24), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_organization_api_keys_organization_id", "organization_api_keys", ["organization_id"])
    op.create_index("ix_organization_api_keys_organization_created", "organization_api_keys", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_organization_api_keys_organization_created", table_name="organization_api_keys")
    op.drop_index("ix_organization_api_keys_organization_id", table_name="organization_api_keys")
    op.drop_table("organization_api_keys")
