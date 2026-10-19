# Per-bus ZKTeco Cloud / ADMS setup

Each bus supports two independently registered machines:

| Driver setup slot | Every scan records |
| --- | --- |
| Boarding machine (ENTRY) | BOARDED — got on the bus |
| Exit machine (EXIT) | ALIGHTED — dropped off |

Each driver manages only their active assigned bus. A machine serial can belong
to only one bus/slot. The two machines can use different enrolled user IDs for
the same student. Machine roles determine direction; no manual IN/OUT selection
is required for these registered machines.

## Driver workflow

1. Sign in as the driver and open **Face ID machines** on the dashboard.
2. Register the boarding machine using its actual serial number, model and local
   timezone (Asia/Colombo by default).
3. Match each student's name to their enrolled user ID/PIN on that machine.
   Only students assigned to this bus are accepted. Leave unenrolled IDs blank.
4. Register the exit machine separately and map its enrolled IDs.
5. On both terminals, set **COMM → Cloud Server / ADMS** to the backend's network
   address and port, **8000** for local testing. Do not use localhost on a device.
6. Refresh connection status. Scan a test student at each machine and check the
   linked parent's Today's Journey. It refreshes recorded events every 10 seconds.

Faces must be enrolled on each terminal using the machine/vendor tools. This
app maps existing user IDs; it does not upload or store face templates/photos.
Names and grade come from the database. Existing seeded/demo students are not
automatically converted into real enrolled students. Add real students through
**Add student**, link their registered parent email, and assign them to the bus.

Drivers can edit mappings, remove a machine, or register a replacement. Remove
the old machine first; recorded attendance remains. Do not reassign an enrolled
PIN to another person while the machine retains old logs: replayed historical
records use the current mapping. Archive/clear old terminal logs using vendor
tools before deliberately repurposing a terminal or PIN.

## Backend setup

Run from `backend/`:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Startup creates the new `face_terminals` registration table for databases using
`create_all`. Versioned databases should run `.venv/bin/alembic upgrade head`.
Existing unversioned databases must first run
`.venv/bin/python -m scripts.upgrade_attendance_schema` if they have not yet
received the attendance upgrade. That script backs up SQLite and allows scans
without GPS; terminal scans do not invent coordinates. The development database
was already upgraded during implementation.

All buses/machines share the same server port. Serial number routing identifies
the correct bus and ENTRY/EXIT role; separate TCP ports per bus are unnecessary.
A remote bus needs a reachable private network/VPN or authenticated gateway.
Legacy ADMS serial numbers are identifiers, not cryptographic authentication:
keep `/iclock/*` on a trusted device network rather than exposing it publicly.
The driver setup APIs require the normal authenticated driver account.

Supported legacy attendance paths:

- GET `/iclock/cdata?SN=SERIAL`: options.
- GET `/iclock/getrequest?SN=SERIAL`: heartbeat.
- POST `/iclock/cdata?SN=SERIAL&table=ATTLOG`: tab-separated PIN, local timestamp,
  status, verification method, optional trailing fields.
- `.aspx` aliases are supported.

Student assignment is checked again at ingestion. Unknown serials, unmapped IDs,
invalid timestamps and students belonging to another bus reject the batch.
Repeated uploads are deduplicated by terminal, bus, student, direction and time.
Cloud ingestion currently updates attendance without dispatching push/SMS alerts.
The terminal's local clock must match its configured timezone. The exact model
and real uploads still need testing: Access Control RTLOG, newer registry/security
handshakes and remote enrollment are not implemented.

## APIs

- GET `/driver/machines`: assigned bus, its students and two configured slots.
- PUT `/driver/machines/ENTRY` or `/EXIT`: serial, model, timezone and `students`
  (a dictionary mapping enrolled PIN strings to student database IDs).
- DELETE `/driver/machines/ENTRY` or `/EXIT`: unregister a slot, retain events.
- GET `/students/{id}/events`: parent-authorized event history.

The legacy `ZKTECO_DEVICES_JSON` environment configuration remains supported for
existing setups and uses its IN/OUT `status_map`. These serials must be removed
from that configuration by an administrator before registering them through the
driver screen. New driver registrations require no environment JSON or shared
bus-level API key. The existing `/device/*` JSON API remains for custom hardware.

ZKTeco setup reference:
https://www.zkteco.co.za/documentation/biotime8/Biotime%208%20%E2%80%93%20Communication%20Settings%20%E2%80%93%20Cloud%20or%20ADMS%20settings.pdf
