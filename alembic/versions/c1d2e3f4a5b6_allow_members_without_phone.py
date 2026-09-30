"""allow member records without phone numbers"""

from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "phone_number", existing_type=sa.String(length=20), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "phone_number", existing_type=sa.String(length=20), nullable=False)