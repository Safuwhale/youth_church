"""add archiving and member tags"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f1a2b3c4d5e6"
down_revision = "3e56a74fcc48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("users", "services", "cell_groups", "attendance_logs"):
        op.add_column(table, sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.create_index(f"ix_{table}_is_archived", table, ["is_archived"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_is_archived", "tags", ["is_archived"], unique=False)
    op.create_table(
        "user_tags",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("user_tags")
    op.drop_index("ix_tags_is_archived", table_name="tags")
    op.drop_table("tags")
    for table in ("attendance_logs", "cell_groups", "services", "users"):
        op.drop_index(f"ix_{table}_is_archived", table_name=table)
        op.drop_column(table, "is_archived")