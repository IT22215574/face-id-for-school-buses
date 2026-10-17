"""Store father and mother mobile numbers per student."""
from alembic import op
import sqlalchemy as sa

revision = "20261017_000003"
down_revision = "20261015_000002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("students", sa.Column("father_phone", sa.String(32), nullable=False, server_default=""))
    op.add_column("students", sa.Column("mother_phone", sa.String(32), nullable=False, server_default=""))


def downgrade():
    op.drop_column("students", "mother_phone")
    op.drop_column("students", "father_phone")
