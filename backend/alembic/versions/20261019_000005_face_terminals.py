"""Register independent entry/exit machines per bus."""
from alembic import op
from app.models.face_terminal import FaceTerminal

revision = "20261019_000005"
down_revision = "20261019_000004"
branch_labels = None
depends_on = None


def upgrade():
    FaceTerminal.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    FaceTerminal.__table__.drop(op.get_bind())
