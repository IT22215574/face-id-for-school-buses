# Architecture and implementation plan

Existing architecture: FastAPI + SQLAlchemy, SQLite development default and PostgreSQL deployment support; Alembic migrations. `StudentTransport` assigns students to buses. `Device` authenticates GPS/event uploads using hashed x-api-key. `BusLocation` retains historical fixes. `Event` powers parent timelines and status (ordered by event time). There is no alternating-scan state machine. Flutter uses Riverpod, Dio and polling; optional Firebase is used for tracking and FCM, with Twilio fallback for notifications. Existing notifications commit separately from attendance. Driver machine registration stores current PIN mappings in JSON; the legacy receiver creates events directly.

Implementation sequence / files:

1. Extend `models/face_terminal.py`, `models/event.py`; add `models/face_ingestion.py` and migration 000007: metadata, historical enrollment, encrypted inbox, direction intervals, event provenance and durable notification jobs.
2. Add `services/face_ingestion.py`: receiver-record interface, durable deduplication, historical resolution, GPS correlation, pending/quarantine handling, supervised classification. Reuse Event and existing notification providers.
3. Add `api/routes/face_admin.py`: admin registration, enrollment, revocation, monitoring, classification and replay; separate secret-authenticated receiver ingestion.
4. Add `scripts/forward_adms.py` for the community receiver's actual JSONL output, and worker for processing/retries/retention. Leave legacy endpoints backward compatible; document their limitations and exclude them from the new deployment path.
5. Extend Flutter administration with a device/enrollment/event screen using existing API client and navigation; expose provenance in existing parent timeline API.
6. Add synthetic tests; run backend suite, migration checks and Flutter analysis. Document receiver assessment, Mac setup, deployment and physical acceptance procedure.

Hardware gate: exact firmware, PUSH version, actual payloads, punch meanings, clock behavior, offline buffer/retry and transport capabilities are unavailable. No hardware compatibility or automated enrollment is claimed. Mode intervals use server UTC boundaries; scans close to a boundary require manual classification because terminal clock alignment is unverified.
