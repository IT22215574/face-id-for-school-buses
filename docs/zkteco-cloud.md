# ZKTeco Cloud / ADMS attendance testing

The dashboard reads `/students/{id}/events` for the selected student's current
local day, displays each boarding/drop-off scan, and refreshes every 10 seconds.
Names, grade, parent and bus assignments come from `/me/transport`. Existing
seeded database records remain until you replace them with enrolled students;
the app does not invent student records or journey times.

## Prepare the database

From `backend/`, install requirements and run `.venv/bin/alembic upgrade head`.
The new migration allows attendance without GPS; the terminal does not provide
GPS, so no coordinates are invented. Back up an existing database before upgrading.
For an unversioned legacy database created using `create_all`, use
`.venv/bin/python -m scripts.upgrade_attendance_schema` instead. This upgrades
only the attendance columns and creates a temporary SQLite backup, printing its
path. Keep that backup somewhere persistent if required. It is safe to rerun.

Create the actual student through the driver's **Add student** screen using the
registered parent's email, or use the existing admin endpoints to link the parent
and assign a bus. This is required for parents to see that student's scans.

Create an active Device record for that bus using the existing provisioning/seed
workflow. `GET /device/students` with its `x-api-key` returns student IDs for that
bus. Enroll each student on the ZKTeco terminal and record its PIN/user ID.
The terminal PIN need not equal the database student ID.

## Configure the receiver

Set this environment variable (or put it in `backend/.env`), replacing every
example value with the actual serial, database bus/student IDs, and enrolled PINs:

```dotenv
ZKTECO_DEVICES_JSON='{"YOUR_SERIAL":{"bus_id":1,"timezone":"Asia/Colombo","students":{"1001":42,"1002":43},"status_map":{"0":"BOARDED","1":"ALIGHTED"}}}'
```

Empty configuration disables terminal access. Start the backend on the network
interface reachable by the machine:

```sh
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On the machine, open **COMM → Cloud Server / ADMS**. Set Server Address to the
backend computer's LAN IP (not localhost), and Server Port to **8000**. The
receiver uses HTTP on a private network. A remote bus needs private VPN routing
or an authenticated gateway. This legacy protocol identifies terminals by serial
number only; do not expose `/iclock/*` directly to the public internet.

Configure the terminal for Attendance PUSH and explicitly select IN when boarding
and OUT when leaving the bus. Defaults map status `0` to BOARDED and `1` to
ALIGHTED; verify these codes on the actual model. Other statuses are rejected
unless explicitly mapped. Never alternate IN/OUT automatically: missed/repeated
scans would produce false drop-off times. Set the machine's clock to the timezone
in the configuration. Morning and afternoon scans appear in time order without
assuming a timetable or classifying an unknown journey.

Supported paths: GET `/iclock/cdata` (options), GET `/iclock/getrequest`
(heartbeat), POST `/iclock/cdata?SN=...&table=ATTLOG` (attendance); `.aspx` aliases
are also accepted. ATTLOG is tab-separated PIN, local timestamp, status,
verification method, plus optional trailing fields. Only attendance records are
requested; face templates/photos are neither downloaded nor enrolled by this app.
The PIN mapping is authoritative; verification codes are model-dependent and are
not used to claim a particular biometric method. Access-control RTLOG, newer
registry/security handshakes and remote enrollment are not implemented. Exact
model/firmware and a real upload are still needed to confirm compatibility.

Unknown serials, unmapped PINs, unassigned students, invalid times and unsupported
statuses reject the whole batch. Repeated uploads are deduplicated by terminal,
bus, student, event type and timestamp. Historical uploads remain historical;
only today's events appear in Today's Journey. Cloud ingestion updates attendance
records; it does not currently dispatch push/SMS notifications.

## Verify without the machine

With a real configured serial/PIN (the values below are examples), send a scan:

```sh
curl -X POST 'http://localhost:8000/iclock/cdata?SN=YOUR_SERIAL&table=ATTLOG' \
  --data-binary $'1001\t2026-10-19 07:30:00\t0\t15\n1001\t2026-10-19 08:15:00\t1\t15'
```

Expect `OK: 2`. These are synthetic test records; use a test student and today's
local date if you want them visible today. Repeat the request to check that no
extra events appear. Then sign in as the linked parent and select the student.
Verify a real IN scan and OUT scan on the terminal before relying on this setup.

For custom HTTP hardware, the existing POST `/device/events` accepts authenticated
JSON with `student_id`, `bus_id`, `event_type` (BOARDED/ALIGHTED), an ISO timestamp
with timezone, latitude/longitude and optional confidence. Its API key must belong
to the student's assigned bus. ZKTeco Cloud uses the ADMS endpoints instead.

ZKTeco setup reference:
https://www.zkteco.co.za/documentation/biotime8/Biotime%208%20%E2%80%93%20Communication%20Settings%20%E2%80%93%20Cloud%20or%20ADMS%20settings.pdf
