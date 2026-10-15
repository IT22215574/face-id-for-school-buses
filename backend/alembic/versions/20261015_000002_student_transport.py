"""Assign students to buses."""
from alembic import op
import sqlalchemy as sa
revision = "20261015_000002"
down_revision = "20241002_000001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("student_transport",
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), primary_key=True),
        sa.Column("bus_id", sa.Integer(), sa.ForeignKey("buses.id"), nullable=False))
    op.create_index("ix_student_transport_bus_id", "student_transport", ["bus_id"])


def downgrade():
    op.drop_table("student_transport")
