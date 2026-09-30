"""performance indexes, trigram search, and monotonic serial sequence"""

from alembic import op

revision = "b7d9a3f21e6c"
down_revision = "4f8d2c9b1a71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE SEQUENCE IF NOT EXISTS user_serial_seq START 1")
    op.execute("""
        SELECT setval(
            'user_serial_seq',
            COALESCE((
                SELECT MAX((regexp_match(serial_number, '^HORYC-([0-9]+)$'))[1]::int)
                FROM users
            ), 0)
        )
    """)
    for table, columns in {
        "users": ["phone_number", "role", "is_active", "cell_group_id", "created_at"],
        "services": ["service_date", "is_active"],
        "attendance_logs": ["user_id", "service_id", "usher_id", "check_in_time"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column], unique=False)
    op.create_index("ix_attendance_logs_service_usher", "attendance_logs", ["service_id", "usher_id"], unique=False)
    op.create_index("ix_attendance_logs_service_time", "attendance_logs", ["service_id", "check_in_time"], unique=False)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_first_name_trgm ON users USING gin (first_name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_last_name_trgm ON users USING gin (last_name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_phone_number_trgm ON users USING gin (phone_number gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_serial_number_trgm ON users USING gin (serial_number gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_role_trgm ON users USING gin (role gin_trgm_ops)")


def downgrade() -> None:
    for index in ("ix_users_role_trgm", "ix_users_serial_number_trgm", "ix_users_phone_number_trgm", "ix_users_last_name_trgm", "ix_users_first_name_trgm"):
        op.execute(f"DROP INDEX IF EXISTS {index}")
    for index, table in (
        ("ix_attendance_logs_service_time", "attendance_logs"),
        ("ix_attendance_logs_service_usher", "attendance_logs"),
        ("ix_attendance_logs_check_in_time", "attendance_logs"),
        ("ix_attendance_logs_usher_id", "attendance_logs"),
        ("ix_attendance_logs_service_id", "attendance_logs"),
        ("ix_attendance_logs_user_id", "attendance_logs"),
        ("ix_services_is_active", "services"),
        ("ix_services_service_date", "services"),
        ("ix_users_created_at", "users"),
        ("ix_users_cell_group_id", "users"),
        ("ix_users_is_active", "users"),
        ("ix_users_role", "users"),
        ("ix_users_phone_number", "users"),
    ):
        op.drop_index(index, table_name=table)
    op.execute("DROP SEQUENCE IF EXISTS user_serial_seq")