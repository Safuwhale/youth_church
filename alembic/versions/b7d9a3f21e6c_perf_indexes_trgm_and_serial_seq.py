"""perf indexes, trigram search, and monotonic serial sequence

Revision ID: b7d9a3f21e6c
Revises: 4f8d2c9b1a71
Create Date: 2026-08-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d9a3f21e6c"
down_revision = "4f8d2c9b1a71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable trigram indexes for fast ILIKE '%term%' contains searches.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Sequence-backed monotonic serial generation.
    op.execute("CREATE SEQUENCE IF NOT EXISTS user_serial_seq START 1")
    op.execute(
        """
        SELECT setval(
            'user_serial_seq',
            COALESCE((
                SELECT MAX((regexp_match(serial_number, '^HORYC-([0-9]+)$'))[1]::int)
                FROM users
            ), 0)
        )
        """
    )

    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("ix_users_cell_group_id", "users", ["cell_group_id"], unique=False)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

    op.create_index("ix_services_service_date", "services", ["service_date"], unique=False)
    op.create_index("ix_services_is_active", "services", ["is_active"], unique=False)

    op.create_index("ix_attendance_logs_user_id", "attendance_logs", ["user_id"], unique=False)
    op.create_index("ix_attendance_logs_service_id", "attendance_logs", ["service_id"], unique=False)
    op.create_index("ix_attendance_logs_usher_id", "attendance_logs", ["usher_id"], unique=False)
    op.create_index("ix_attendance_logs_check_in_time", "attendance_logs", ["check_in_time"], unique=False)
    op.create_index("ix_attendance_logs_service_usher", "attendance_logs", ["service_id", "usher_id"], unique=False)
    op.create_index("ix_attendance_logs_service_time", "attendance_logs", ["service_id", "check_in_time"], unique=False)

    op.execute("CREATE INDEX IF NOT EXISTS ix_users_first_name_trgm ON users USING gin (first_name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_last_name_trgm ON users USING gin (last_name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_phone_number_trgm ON users USING gin (phone_number gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_serial_number_trgm ON users USING gin (serial_number gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_role_trgm ON users USING gin (role gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_role_trgm")
    op.execute("DROP INDEX IF EXISTS ix_users_serial_number_trgm")
    op.execute("DROP INDEX IF EXISTS ix_users_phone_number_trgm")
    op.execute("DROP INDEX IF EXISTS ix_users_last_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_users_first_name_trgm")

    op.drop_index("ix_attendance_logs_service_time", table_name="attendance_logs")
    op.drop_index("ix_attendance_logs_service_usher", table_name="attendance_logs")
    op.drop_index("ix_attendance_logs_check_in_time", table_name="attendance_logs")
    op.drop_index("ix_attendance_logs_usher_id", table_name="attendance_logs")
    op.drop_index("ix_attendance_logs_service_id", table_name="attendance_logs")
    op.drop_index("ix_attendance_logs_user_id", table_name="attendance_logs")

    op.drop_index("ix_services_is_active", table_name="services")
    op.drop_index("ix_services_service_date", table_name="services")

    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_cell_group_id", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_phone_number", table_name="users")

    op.execute("DROP SEQUENCE IF EXISTS user_serial_seq")
