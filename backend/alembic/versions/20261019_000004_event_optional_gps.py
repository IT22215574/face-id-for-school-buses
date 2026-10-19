"""Allow attendance terminals without GPS to record scans."""
from alembic import op
import sqlalchemy as sa

revision = "20261019_000004"
down_revision = "20261017_000003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("events") as batch:
        batch.add_column(sa.Column("ingestion_key", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_events_ingestion_key", ["ingestion_key"])
        batch.alter_column("lat", existing_type=sa.Float(), nullable=True)
        batch.alter_column("lng", existing_type=sa.Float(), nullable=True)


def downgrade():
    # Refuse to invent GPS coordinates for existing scans.
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT COUNT(*) FROM events WHERE lat IS NULL OR lng IS NULL")).scalar():
        raise RuntimeError("Cannot downgrade while scans without GPS exist")
    with op.batch_alter_table("events") as batch:
        batch.drop_constraint("uq_events_ingestion_key", type_="unique")
        batch.drop_column("ingestion_key")
        batch.alter_column("lat", existing_type=sa.Float(), nullable=False)
        batch.alter_column("lng", existing_type=sa.Float(), nullable=False)
