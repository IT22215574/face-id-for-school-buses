"""Upgrade only attendance columns for legacy create_all databases.

Versioned databases should use alembic upgrade head instead. SQLite is backed up
using its online backup API before altering data. No student records are changed.
"""
import importlib.util
import sqlite3
import tempfile
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.db.session import engine


def main():
    with engine.connect() as connection:
        inspector = inspect(connection)
        if 'alembic_version' in inspector.get_table_names():
            raise SystemExit('Versioned database: run alembic upgrade head instead.')
        columns = {c['name']: c for c in inspector.get_columns('events')}
        if 'ingestion_key' in columns and columns['lat']['nullable'] and columns['lng']['nullable']:
            print('Attendance schema is already up to date.')
            return
        if 'ingestion_key' in columns:
            raise SystemExit('Partial attendance upgrade found; inspect schema before continuing.')
    if engine.dialect.name == 'sqlite' and engine.url.database != ':memory:':
        backup_path = Path(tempfile.mkdtemp(prefix='schoolbus-attendance-backup-')) / 'schoolbus.db'
        with sqlite3.connect(engine.url.database) as source, sqlite3.connect(backup_path) as destination:
            source.backup(destination)
        print(f'Database backup: {backup_path}')
    elif engine.dialect.name != 'sqlite':
        raise SystemExit('Use a reviewed Alembic migration for non-SQLite legacy databases.')
    migration = Path(__file__).resolve().parents[1] / 'alembic/versions/20261019_000004_event_optional_gps.py'
    spec = importlib.util.spec_from_file_location('attendance_migration', migration)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
    print('Attendance schema upgraded. Student records retained.')


if __name__ == '__main__':
    main()
