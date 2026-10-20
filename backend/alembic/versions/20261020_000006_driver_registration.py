"""Encrypted driver onboarding details."""
from alembic import op
from app.models.driver_registration import DriverRegistration
revision = '20261020_000006'
down_revision = '20261019_000005'
branch_labels = None
depends_on = None


def upgrade():
    DriverRegistration.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    DriverRegistration.__table__.drop(op.get_bind())
