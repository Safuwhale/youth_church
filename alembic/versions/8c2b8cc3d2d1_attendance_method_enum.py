"""attendance method enum"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8c2b8cc3d2d1"
down_revision = "53a34c53264e"
branch_labels = None
depends_on = None

attendance_method_enum = postgresql.ENUM(
    "QR_SCAN",
    "SELF_SCAN",
    "MANUAL",
    name="check_in_method_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    attendance_method_enum.create(bind, checkfirst=True)
    op.alter_column(
        "attendance_logs",
        "check_in_method",
        existing_type=sa.String(length=20),
        type_=attendance_method_enum,
        postgresql_using="check_in_method::check_in_method_enum",
        existing_nullable=True,
        nullable=False,
        server_default=sa.text("'QR_SCAN'::check_in_method_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "attendance_logs",
        "check_in_method",
        existing_type=attendance_method_enum,
        type_=sa.String(length=20),
        postgresql_using="check_in_method::text",
        existing_nullable=False,
        nullable=True,
        server_default=sa.text("'QR_SCAN'"),
    )
    attendance_method_enum.drop(op.get_bind(), checkfirst=True)
