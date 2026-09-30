"""remove completed claim profile state"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "is_claimed")
    op.create_index("ix_attendance_logs_service_archived", "attendance_logs", ["service_id", "is_archived"])
    op.create_index("ix_attendance_logs_user_archived", "attendance_logs", ["user_id", "is_archived"])
    op.create_index("ix_services_date_archived", "services", ["service_date", "is_archived"])


def downgrade() -> None:
    op.drop_index("ix_services_date_archived", table_name="services")
    op.drop_index("ix_attendance_logs_user_archived", table_name="attendance_logs")
    op.drop_index("ix_attendance_logs_service_archived", table_name="attendance_logs")
    op.add_column("users", sa.Column("is_claimed", sa.Boolean(), nullable=True))