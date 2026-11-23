"""Add per-user session version for server-side token revocation.

Revision ID: 0005_session_revocation
Revises: 0004_saved_analyses
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_session_revocation"
down_revision = "0004_saved_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("users", "session_version", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "session_version")
