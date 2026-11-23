"""Add saved numeric distribution analyses."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_saved_analyses"
down_revision = "0003_pipelines"
branch_labels = None
depends_on = None

json_values = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "saved_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("column_name", sa.String(length=160), nullable=False),
        sa.Column("profile", json_values, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_analyses_organization_id", "saved_analyses", ["organization_id"])
    op.create_index("ix_saved_analyses_organization_created", "saved_analyses", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_saved_analyses_organization_created", table_name="saved_analyses")
    op.drop_index("ix_saved_analyses_organization_id", table_name="saved_analyses")
    op.drop_table("saved_analyses")
