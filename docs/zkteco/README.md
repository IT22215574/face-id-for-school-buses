# Face terminal integration — hardware acceptance pending

Software path: isolated community receiver → attendance JSONL → authenticated forwarding adapter → encrypted SQL inbox → worker → existing Event table + notification outbox → existing Flutter parent timeline and new admin monitoring.

No real M2F PRO-LR scan has been tested. Do not deploy this as a verified terminal integration until the acceptance procedure below succeeds. No Doer Plus dependency or server/mobile face recognition is introduced.

## Receiver evaluation and protocol evidence

Reviewed upstream revision `f90040c735f04a3ce364e02ce6c91b30c2d4bcd1` of [Vibhav-Aggarwal/zkteco-adms-server](https://github.com/Vibhav-Aggarwal/zkteco-adms-server/tree/f90040c735f04a3ce364e02ce6c91b30c2d4bcd1). Its license file is Apache-2.0. Dependencies: FastAPI and Uvicorn. No upstream source is vendored here.

The inspected `server.py` implements `.aspx` registration, attendance/operation uploads, command polling/results, ping and health. Its attendance file provides `ts`, `sn`, `pin`, `time`, `status`, `verify`, `raw`; the adapter consumes that interface. The README lists other tested models, not M2F PRO-LR. These claims are not independent hardware verification.

Source review found no terminal authentication, unbounded request bodies, unsanitized serial-derived filenames, plaintext enrollment storage, a global command queue and file appends without fsync. This is a test receiver requiring isolation. Our wrapper allowlists serials, bounds uploads, rejects non-attendance POSTs, disables commands and fsyncs attendance data before upstream acknowledgement. It does not add terminal authentication or verify vendor acknowledgement semantics.

[Official model announcement](https://zkteco.com/en/New_Launches/M2-LR_M2F_PRO-LR) describes face recognition and network interfaces, but does not establish firmware-specific wire compatibility. [ZKTeco's PUSH information page](https://www.zkteco.com.br/produto/protocolo-push/) describes an HTTP integration and asks developers to request protocol documentation. Exact official PUSH SDK documentation for this terminal/firmware was not available in the project or retrieved from an official public source. Upstream references a third-party hosted protocol document; that is not firmware certification. Obtain the applicable official SDK from the vendor before confirming protocol operations, status/verification meanings or ACK/retry behavior.

No punch-state or verification number is interpreted as a confirmed model-specific capability. Direction uses checked-clock mode intervals or per-scan supervised classification. No automated enrollment, biometric transfer, terminal command, TLS or offline-buffer capability is claimed.

## Data and operational behavior

- Reuses SQLAlchemy, Alembic and the configured SQLite/PostgreSQL database. `Event` remains the parent attendance record. Enrollment history records effective intervals and consent references; current JSON driver mappings are not used by this adapter.
- Bus assignment, serial and timezone are immutable through the admin API. Retain historical serials; moving a terminal between buses is intentionally unsupported until assignment-history support is implemented. The existing one-ENTRY/one-EXIT slot constraint remains. Disable a device instead of deleting its history. Replacements needing an occupied slot require a reviewed migration; do not reuse a serial or edit SQL history casually.
- Inbox identity is SHA-256(serial + original row). There is no verified vendor event ID. Identical rows in the same terminal second collapse, including two genuine indistinguishable scans. Same-student, same-direction scans within the configurable 10-second window share one Event and notification job. Audit rows remain available. This debounce is an application policy, not a vendor protocol guarantee.
- Invalid/mismatched timestamps are quarantined; unknown mappings, unchecked clocks, uncertain direction and future timestamps remain pending. Pending records require operator review and safe reprocessing, rather than endless automatic retries.
- Clock verification covers only scans after the recorded check and expires within 24 hours. It must be based on observed terminal clock error below the configured direction guard. Changes to power, clock or timezone invalidate the operational assurance: stop automatic classification and repeat the physical check. Delayed old scans lacking a contemporaneous check require individual classification. A historical mode never uses the current mode to reinterpret an older scan.
- GPS uses original scan UTC, historical `BusLocation.gps_time`, ±120 seconds and reported accuracy ≤100 m by default. Missing accuracy is not assumed accurate. No qualifying fix means null coordinates: STALE when GPS history exists, otherwise UNAVAILABLE. Phone GPS uploads now include accuracy; old clients still work but their fixes may not qualify. The separate Firebase sharing feature stores current positions; it is not historical attendance evidence. Use existing driver GPS ingestion or `/device/location` for historical fixes.
- Inbox payloads are Fernet encrypted with a dedicated required key. No raw payload read API exists. Worker purges encrypted payloads after 30 days while retaining deduplication identity and audit/provenance. Restricted receiver JSONL and backups also need retention controls; the database purge does not remove those files. Original device time is retained in the inbox and `Event.event_time`; backend receipt time is separate.
- Notification jobs are committed atomically with Event creation. Existing FCM/SMS providers are reused with original event date/time, explicitly labelled UTC. Known undelivered jobs retry with backoff up to 10 attempts. Provider exceptions are UNCERTAIN; an interrupted send stays SENDING. Neither is retried automatically. External delivery cannot be exactly-once without provider idempotency/reconciliation. Stop the worker, review provider logs, then use **Review notification** to record DELIVERED or authorize RETRY with evidence. The admin reconciliation endpoint audits the decision. Duplicate/replayed or unclassified scans create no additional jobs.
- Device ONLINE/OFFLINE is derived from recent accepted attendance uploads (5 minutes), not a proven connectivity heartbeat. Idle terminals can appear offline. This distinction is shown in Flutter as last attendance upload. A real authenticated heartbeat integration remains firmware dependent.

## Local macOS setup

Use Python 3.11 for the pinned backend dependencies. Preserve the existing development database and take a backup before migrations. Do not run commands against the production database for the first test.

From repository root:

```sh
python3.11 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

Export configuration in each relevant terminal (or use an untracked `backend/.env` for backend settings):

```sh
export DATABASE_URL=sqlite:///./schoolbus.db
export FACE_ADAPTER_TOKEN="$(backend/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export FACE_RAW_ENCRYPTION_KEY="$(backend/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

The additional settings and defaults are listed in [adapter.env.example](adapter.env.example). Keep these generated values consistent across restarts. Store them securely; changing the encryption key without key rotation makes retained payloads unreadable. Do not put either value in Flutter. Configure existing JWT and notification credentials as described in the root README. Use absolute database URLs if starting workers from different directories.

Start the backend from `backend/`:

```sh
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Migration 000007 extends existing tables; it does not replace the database. The old terminal migration is frozen to its original schema so clean installs do not import future ORM columns. Existing installations created using `create_all()` without Alembic history need a schema audit and correct baseline before upgrading; do not stamp blindly. Startup `create_all()` does not migrate existing tables.

In a separate private working directory, fetch the receiver (keep its license):

```sh
git clone https://github.com/Vibhav-Aggarwal/zkteco-adms-server.git zkteco-adms-server
cd zkteco-adms-server
git checkout f90040c735f04a3ce364e02ce6c91b30c2d4bcd1
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Back at this repository root, configure real paths and the real serial copied from the physical terminal:

```sh
umask 077
mkdir -p .local/adms/data .local/adms/log
export ADMS_SOURCE_DIR=/absolute/path/to/zkteco-adms-server
export ADMS_ALLOWED_SERIALS=REPLACE_WITH_REAL_SERIAL
export ADMS_DATA_DIR="$PWD/.local/adms/data"
export ADMS_EVENT_LOG="$PWD/.local/adms/log/events.jsonl"
export ADMS_CMD_QUEUE="$PWD/.local/adms/disabled-commands.jsonl"
backend/.venv/bin/uvicorn integrations.adms_receiver:app --app-dir backend --host 0.0.0.0 --port 8081 --workers 1
```

This invokes the inspected upstream app through the isolated wrapper. The upstream's own documented start command is `uvicorn server:app --host 0.0.0.0 --port 8081`; use the wrapper for this test to enforce attendance-only handling and durable writes. Its unchanged handshake advertises additional data types that our wrapper rejects; confirm attendance-only settings with the vendor before hardware testing. Unsupported endpoints/tables must not be treated as successfully ingested.

Allow TCP 8081 only from the terminal on the test LAN. Keep application `/iclock` routes inaccessible to terminal traffic: they are the preserved legacy implementation and bypass this inbox/outbox path. Do not configure both paths simultaneously. A serial allowlist is not authentication. Do not expose this listener directly to the Internet.

Verify from another computer on the same LAN:

```sh
curl http://MAC_LAN_IP:8081/health
nc -vz MAC_LAN_IP 8081
```

Check that the terminal has a route to the Mac (Wi-Fi client isolation may block it). Record firmware, hardware platform, PUSH version, clock and cloud settings. Configure the actual server menu only as permitted by the exact manual: Mac LAN IP and port 8081. Do not assume a menu path or HTTPS toggle exists. Keep enrollment on the terminal. No command queue should be populated.

From `backend/`, run forwarding and worker in separate terminals with the same credentials and database:

```sh
.venv/bin/python scripts/forward_adms.py --directory /absolute/path/to/.local/adms/data --state /absolute/path/to/.local/adms/cursor.json --url http://127.0.0.1:8000
PYTHONPATH=. .venv/bin/python scripts/face_worker.py
```

The forwarder only advances its fsync-backed cursor after HTTP 202. Restarting or removing the cursor replays safely. It stops on malformed/oversized rows or replaced/truncated files without skipping data. Keep one forwarder per directory. Archive source files securely before deliberate rotation and checkpoint reset. A revoked/unknown serial stops that file for operator inspection. Receiver spool storage is plaintext attendance metadata and needs encrypted disk, restrictive permissions and scheduled retention.

## Registration, enrollment and Flutter acceptance

1. Sign in as ADMIN in Flutter. Open **Face Recognition Devices** from administration. Register the real serial, model, observed firmware, timezone and assigned bus ID. For a device already in the legacy registry, stop its old route first, then choose **Use receiver adapter** and create fresh confirmed mappings at the cutover time. Managed devices reject legacy `/iclock` ingestion and driver edits. The slot is ENTRY or EXIT, but slot alone does not classify direction in this new path.
2. Select an existing student assigned to the bus. Assign a terminal user ID, obtain guardian consent in the school's consent register, enroll the face directly on the terminal, then use **Confirm enrollment**. Supply the true effective start with timezone and consent reference. Enrollment history is separate from legacy driver JSON mappings.
3. Observe the terminal clock against trusted UTC, then use **Verify clock** with the observed absolute error, expiry within 24 hours and evidence reference. This never changes the device clock. Set boarding/alighting mode before scanning (ADMIN or the assigned driver). Wait beyond the guard interval or classify the boundary scan manually.
4. Start the driver's existing GPS sharing route that posts `/driver/location`, or post an authenticated fix with original `gps_time` and `accuracy_m` to `/device/location`. Existing Firebase-only location sharing does not provide SQL history. Do not fabricate a GPS fix as real data.
5. Scan an enrolled face. Confirm that an actual `attlog_REAL_SERIAL.jsonl` row appears in the restricted receiver directory. Inspect only with an authorized operator on the Mac; do not paste enrollment files, secrets or children's identifiers into tickets. Verify PIN, local scan time and serial against the device's attendance screen. Record only redacted evidence in the acceptance report.
6. Confirm one inbox row and one Event in Flutter monitoring, the correct student/bus, original time, receipt time, direction source, GPS availability and delayed indicator. Pending records show the reason. Correct mapping intervals if justified, then **Reprocess**, or use supervised **Classify scan** with evidence. Quarantined invalid timestamps are not silently repaired.
7. Sign in as the linked parent: today's valid scans appear in the existing journey view within its 10-second polling interval. Earlier-day delayed events are in the existing date-filtered events API and admin history; the existing today's-journey widget intentionally does not display previous days. Confirm a real FCM/SMS notification using configured test recipients and original UTC scan time. Inspect outbox statuses in monitoring.
8. Replay the identical receiver file: confirm one Event/job, increased duplicate count and no second alert. Repeat the face scan within the debounce window and verify DUPLICATE_SCAN.
9. Disconnect and reconnect network under supervision. Record whether the actual terminal buffers and retries, captures original timestamps and honors ACKs. Change direction during the outage and ensure old scans use their historical intervals or remain pending. Restart receiver/forwarder/worker, reverse upload order and simulate backend downtime. Confirm recovery from the durable spool/inbox before trusting production operation.
10. End a mapping when consent is withdrawn; remove the biometric enrollment on the physical terminal and record deletion in the consent register. Backend mapping termination does not delete device biometrics. Re-enroll only after consent and a new non-overlapping mapping interval. Backend data erasure and backup expiry must follow the school's documented retention policy.

Integration acceptance requires a real M2F PRO-LR face scan received, normalized, committed and displayed in Flutter, with redacted evidence and notification verification. That acceptance has not happened in this development session.

## Tests

From `backend/`: `.venv/bin/python -m pytest -q`. To include the actual pinned upstream-source contract test, set `ADMS_TEST_SOURCE_DIR=/absolute/path/to/zkteco-adms-server` for that command. The wrapper checks the reviewed `server.py` SHA-256 and refuses source drift. All records in `tests/test_face_ingestion.py` are synthetic. They test software contracts, not wire or firmware compatibility. Test isolated database migrations before upgrading an existing installation. Flutter changes use existing Riverpod/Dio/navigation patterns and can be checked with `flutter analyze`.

## Production design and remaining gates

Run cloud FastAPI behind an authenticated application gateway; route terminal networks through per-bus router VPNs to a dedicated ingress subnet. Give each bus independent network credentials and revocation. The terminal may speak plain HTTP inside its private segment; do not claim device TLS/mTLS/signatures without firmware evidence. Authenticate the forwarder to the backend with the dedicated adapter token over HTTPS or private VPN; rotate it in secret management. Restrict `/internal/face-receiver` by network as well as token, and block public `/iclock`. Configure request-size limits and per-source rate limits at the ingress proxy.

Use the existing PostgreSQL deployment for multiple API/worker processes. SQL inbox/outbox tables provide the durable queue without introducing another database engine. Workers claim notification jobs atomically; processing serializes per inbox/student. Use one worker for SQLite development. Monitor received/pending/quarantined/duplicate counts, spool disk space, oldest queued age, notification FAILED/UNCERTAIN/SENDING jobs, terminal upload age and clock verification expiry. Central logs must contain IDs and statuses, not raw payloads, tokens, images or templates. Keep database/spool volumes encrypted, back them up, restrict access and test restores together with cursor/dedup state and encryption keys.

Before production, verify the official firmware protocol and ACK/retry semantics; prove buffer retention and power-failure behavior; test VPN routing and clock drift under 4G loss; load-test concurrent PostgreSQL workers; implement authenticated heartbeat reporting if required; establish a provider reconciliation runbook; define consent/deletion responsibilities and spool/backup retention; and add assignment-history/slot lifecycle support before moving/replacing registered terminals. The wrapper remains an isolated compatibility-test harness, not a certified production PUSH receiver.

## Validation recorded on 2026-10-24

- Backend full suite with `ADMS_TEST_SOURCE_DIR` pointing at the pinned checkout: **106 passed**. Includes independent-connection concurrent ingestion/processing, commit-failure recovery, outbox reconciliation, migration upgrade/downgrade data preservation, forwarding cursor recovery, and the actual upstream-source wrapper contract using synthetic records.
- Existing Flutter full suite: **30 passed**. Subsequent targeted administration and updated delayed-journey tests: **3 passed**, including two new administration tests.
- Dart analysis of changed application files: no issues. Analysis of all `lib/` reports three existing `prefer_const_constructors` informational findings in `child_detail_screen.dart`.
- `git diff --check`: clean. No production database migration, deployment, provider delivery or physical terminal test was performed.
