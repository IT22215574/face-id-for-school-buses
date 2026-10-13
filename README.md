# School Bus Parent App

This monorepo contains a production-ready starter implementation for a School Bus Parent App with:

- FastAPI backend for parent auth, live bus tracking, device ingestion, and event notifications
- PostgreSQL + SQLAlchemy + Alembic migration setup
- Flutter mobile app skeleton for auth, dashboard, child detail, bus map, notifications, and settings
- Dockerized deployment setup for the API, Postgres, and Redis

## Repository structure

- backend/ – FastAPI application and Alembic migrations
- flutter_app/ – Flutter project skeleton
- docs/ – Postman/Bruno collection export
- docker-compose.yml – local stack deployment
- .env.example – environment variables

## Backend architecture

The backend is organized as:

- app/api – REST and WebSocket routes
- app/core – config, security, logging, and rate limiting
- app/models – SQLAlchemy ORM models
- app/schemas – input/output request validation models
- app/services – auth, event, bus, and notification logic
- app/db – database setup and Alembic support

## Quick start

1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

2. Start Postgres and Redis locally:
   ```bash
   docker compose up -d db redis
   ```

3. Create and activate a virtual environment:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Initialize the schema:
   ```bash
   alembic upgrade head
   ```

5. Seed demo data:
   ```bash
   PYTHONPATH=. python scripts/seed_db.py
   ```

6. Run the API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Docker deployment

```bash
docker compose up --build
```

The API will be reachable at http://localhost:8000, Postgres at localhost:5432, and Redis at localhost:6379.

## Flutter app

Prerequisites:

- Flutter SDK installed
- Firebase project configured for Android/iOS
- Google Maps API key added to app configuration

Run the app:

```bash
cd flutter_app
flutter pub get
flutter run
```

## Acceptance test checklist

- Parent login and linked students load successfully
- Device BOARDED event triggers parent notification flow
- Push failures fall back to SMS if configured
- Bus map receives updates within 10 seconds
- Event history returns ordered results
- Unauthorized device requests return 401

## Notes

- JWT access and refresh tokens are issued and validated with a strong secret.
- Device API keys are hashed before storage.
- Notification logic logs every push/sms attempt in the notifications table.
- WebSocket endpoint supports real-time updates to the bus location stream.

## Security considerations for production

- Keep JWT_SECRET in a secure secret manager.
- Use HTTPS in production.
- Store FCM credentials as secure secret material.
- Configure Twilio and Google Maps keys in the production environment.
- Add additional operational monitoring, log retention, and rate limiting policies as needed.

## Parent and driver development credentials

The seed command creates these local demo accounts:

| Account | Email | Password |
| --- | --- | --- |
| Parent | parent@example.com | password123 |
| Driver | driver@example.com | driver123 |

These accounts have been created in the local SQLite database at `backend/schoolbus.db`. Start the API from `backend/` with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`. Docker/Postgres uses a separate database: run `docker compose exec api python -m scripts.seed_db` after starting that stack to create the same demo accounts there.

The Flutter sign-in screen authenticates through `/auth/login` and obtains the server-authorized role through `/me`. Parent accounts open child selection; driver accounts open the driver dashboard. Use **Sign out** on either dashboard to log in with another account. Transport screen data remains a UI preview.

For a physical phone, use the development computer's LAN address:

```sh
flutter run --dart-define=API_BASE_URL=http://YOUR_COMPUTER_IP:8000
```

The default API address is `http://localhost:8000`. Android emulators usually require `http://10.0.2.2:8000`. The demo credentials are for local development.
