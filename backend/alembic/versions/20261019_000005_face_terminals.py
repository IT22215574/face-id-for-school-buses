"""Register independent entry/exit machines per bus."""
from alembic import op
import sqlalchemy as sa

revision = "20261019_000005"
down_revision = "20261019_000004"
branch_labels = None
depends_on = None


def upgrade():
    # Freeze the original schema; importing live ORM models changes old migrations.
    if sa.inspect(op.get_bind()).has_table('face_terminals'):
        return
    op.create_table('face_terminals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bus_id', sa.Integer(), sa.ForeignKey('buses.id'), nullable=False),
        sa.Column('serial', sa.String(40), nullable=False, unique=True),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('timezone', sa.String(80), nullable=False),
        sa.Column('students', sa.JSON(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime()),
        sa.UniqueConstraint('bus_id', 'role', name='uq_face_terminal_bus_role'))
    op.create_index('ix_face_terminals_bus_id', 'face_terminals', ['bus_id'])


def downgrade():
    op.drop_table('face_terminals')
