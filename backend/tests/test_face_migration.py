"""Migration round-trip preserves pre-adapter attendance and device records."""
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from app.core.config import get_settings


def test_upgrade_and_downgrade_preserve_legacy_data(tmp_path, monkeypatch):
    root = Path(__file__).parents[1]
    url = f'sqlite:///{tmp_path}/migration.db'
    monkeypatch.setattr(get_settings(), 'DATABASE_URL', url)
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    command.upgrade(config, '20261020_000006')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO buses (id, plate_no, device_id, route_name, created_at) VALUES (1, 'SYNTHETIC', 'test', 'Test', '2026-10-20')"))
        db.execute(text("INSERT INTO students (id, name, grade, school_id, created_at) VALUES (1, 'Synthetic', '5', 'Test', '2026-10-20')"))
        db.execute(text("INSERT INTO face_terminals (id, bus_id, serial, role, model, timezone, students) VALUES (1, 1, 'SYNTHETIC', 'ENTRY', 'Unverified', 'Asia/Colombo', '{}')"))
        db.execute(text("INSERT INTO events (id, student_id, bus_id, event_type, event_time, lat, lng, source, created_at) VALUES (1, 1, 1, 'BOARDED', '2026-10-20 02:00:00', NULL, NULL, 'DEVICE', '2026-10-20')"))
    command.upgrade(config, 'head')
    with engine.connect() as db:
        row = db.execute(text('SELECT serial, enabled, adapter_managed FROM face_terminals')).one()
        assert row == ('SYNTHETIC', 1, 0)
        assert db.execute(text('SELECT source, lat, received_at FROM events')).one() == ('DEVICE', None, None)
        assert inspect(db).has_table('face_notification_jobs')
    command.downgrade(config, '20261020_000006')
    command.upgrade(config, 'head')
    with engine.connect() as db:
        assert db.execute(text('SELECT COUNT(*) FROM events')).scalar() == 1
        assert db.execute(text('SELECT serial FROM face_terminals')).scalar() == 'SYNTHETIC'
    engine.dispose()
