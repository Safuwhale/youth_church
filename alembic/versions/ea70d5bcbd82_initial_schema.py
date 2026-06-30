"""initial schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "ea70d5bcbd82"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "cell_groups" not in existing_tables:
        op.create_table(
            "cell_groups",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("location", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("serial_number", sa.String(length=20), nullable=False),
            sa.Column("first_name", sa.String(length=50), nullable=False),
            sa.Column("last_name", sa.String(length=50), nullable=False),
            sa.Column("phone_number", sa.String(length=20), nullable=False),
            sa.Column("whatsapp_number", sa.String(length=20), nullable=True),
            sa.Column("dob", sa.Date(), nullable=True),
            sa.Column("location_zone", sa.String(length=100), nullable=True),
            sa.Column("contact_person_name", sa.String(length=100), nullable=True),
            sa.Column("contact_person_relation", sa.String(length=50), nullable=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("cell_group_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["cell_group_id"], ["cell_groups.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("phone_number"),
            sa.UniqueConstraint("serial_number"),
        )
        op.create_index(op.f("ix_users_serial_number"), "users", ["serial_number"], unique=False)

    if "services" not in existing_tables:
        op.create_table(
            "services",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("time_started", sa.DateTime(timezone=True), nullable=True),
            sa.Column("time_closed", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if "attendance_logs" not in existing_tables:
        op.create_table(
            "attendance_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("usher_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("check_in_time", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("check_in_method", sa.String(length=20), nullable=True),
            sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["usher_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "service_id", name="_user_service_uc"),
        )


def downgrade() -> None:
    op.drop_table("attendance_logs")
    op.drop_table("services")
    op.drop_index(op.f("ix_users_serial_number"), table_name="users")
    op.drop_table("users")
    op.drop_table("cell_groups")
