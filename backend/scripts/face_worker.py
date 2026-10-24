"""Database-backed attendance queue; run one worker for SQLite development."""
import argparse
import logging
import time
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal
from app.models.face_ingestion import FaceInbox, FaceNotificationJob
from app.services.face_ingestion import process, deliver_job, purge_raw


def run_once():
    with SessionLocal() as db:
        ids = [r.id for r in db.query(FaceInbox).filter_by(processing_status='RECEIVED').order_by(FaceInbox.id).limit(100)]
        for inbox_id in ids:
            try:
                process(db, inbox_id)
            except SQLAlchemyError:
                db.rollback()
                logging.error('Attendance database error; retained inbox %s for retry', inbox_id)
        jobs = [r.id for r in db.query(FaceNotificationJob).filter(FaceNotificationJob.status.in_(['PENDING', 'FAILED']),
            FaceNotificationJob.attempts < 10, FaceNotificationJob.next_attempt_at <= datetime.utcnow()).limit(100)]
        for job_id in jobs:
            deliver_job(db, job_id)
        purge_raw(db)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    while True:
        try:
            run_once()
        except SQLAlchemyError:
            logging.error('Database unavailable; queue retained for retry')
            if args.once:
                raise
        if args.once:
            break
        time.sleep(5)
