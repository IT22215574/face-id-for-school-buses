"""Durable face attendance adapter and provenance."""
from alembic import op
import sqlalchemy as sa
revision = '20261023_000007'
down_revision = '20261020_000006'
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table('face_terminals') as batch:
        batch.add_column(sa.Column('adapter_managed', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('clock_checked_at', sa.DateTime()))
        batch.add_column(sa.Column('clock_verified_until', sa.DateTime()))
        batch.add_column(sa.Column('device_name', sa.String(100)))
        batch.add_column(sa.Column('firmware_version', sa.String(100)))
        batch.add_column(sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
        batch.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    with op.batch_alter_table('bus_locations') as batch:
        batch.add_column(sa.Column('accuracy_m', sa.Float()))
    with op.batch_alter_table('events') as batch:
        batch.add_column(sa.Column('source_device_id', sa.Integer(), sa.ForeignKey('face_terminals.id', name='fk_event_face_terminal')))
        for name, kind in [('received_at', sa.DateTime()), ('direction_source', sa.String(30)),
                           ('gps_status', sa.String(20)), ('gps_timestamp', sa.DateTime()),
                           ('gps_source', sa.String(30)), ('gps_accuracy_m', sa.Float()), ('is_delayed', sa.Boolean())]:
            batch.add_column(sa.Column(name, kind))
    op.create_table('face_enrollments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('face_terminals.id'), nullable=False),
        sa.Column('terminal_user_id', sa.String(32), nullable=False),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_until', sa.DateTime()),
        sa.Column('consent_reference', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('device_id', 'terminal_user_id', 'effective_from'))
    op.create_index('ix_face_enrollments_device_id', 'face_enrollments', ['device_id'])
    op.create_table('face_directions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('face_terminals.id'), nullable=False),
        sa.Column('event_type', sa.String(10), nullable=False),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_until', sa.DateTime()),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('parents.id'), nullable=False))
    op.create_index('ix_face_directions_device_id', 'face_directions', ['device_id'])
    op.create_table('face_inbox',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('face_terminals.id'), nullable=False),
        sa.Column('deduplication_key', sa.String(64), nullable=False, unique=True),
        sa.Column('raw_payload', sa.Text()),
        sa.Column('terminal_user_id', sa.String(32), nullable=False),
        sa.Column('device_event_time', sa.DateTime()),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('processing_status', sa.String(30), nullable=False),
        sa.Column('processing_error', sa.String(200)),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id')),
        sa.Column('duplicate_count', sa.Integer(), nullable=False),
        sa.Column('override_direction', sa.String(10)),
        sa.Column('override_actor_id', sa.Integer(), sa.ForeignKey('parents.id')),
        sa.Column('override_reason', sa.String(200)))
    op.create_index('ix_face_inbox_device_id', 'face_inbox', ['device_id'])
    op.create_index('ix_face_inbox_processing_status', 'face_inbox', ['processing_status'])
    op.create_table('face_notification_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('parents.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.String(200)),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('event_id', 'parent_id'))


def downgrade():
    for name in ('face_notification_jobs', 'face_inbox', 'face_directions', 'face_enrollments'):
        op.drop_table(name)
    with op.batch_alter_table('bus_locations') as batch:
        batch.drop_column('accuracy_m')
    with op.batch_alter_table('events') as batch:
        batch.drop_constraint('fk_event_face_terminal', type_='foreignkey')
        for name in ('source_device_id', 'received_at', 'direction_source', 'gps_status', 'gps_timestamp', 'gps_source', 'gps_accuracy_m', 'is_delayed'):
            batch.drop_column(name)
    with op.batch_alter_table('face_terminals') as batch:
        for name in ('device_name', 'firmware_version', 'enabled', 'created_at', 'updated_at', 'clock_checked_at', 'clock_verified_until', 'adapter_managed'):
            batch.drop_column(name)
