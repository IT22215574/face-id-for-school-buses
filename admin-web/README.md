# admin-web

React admin workspace for the same FastAPI backend and database used by Flutter.
Requires Node.js 20.19+ or 22.12+.

## Development

Start the existing backend on port 8000. In a second terminal, from the repository root:

```sh
cd admin-web
npm install
npm run dev
```

Open http://localhost:5173/admin-web/ and sign in with an existing ADMIN account.
The Vite development proxy forwards `/api` requests to http://127.0.0.1:8000.
To point the proxy elsewhere, run `ADMIN_API_URL=http://host:8000 npm run dev`.

## Serve from the backend

```sh
cd admin-web
npm ci
npm run build
```

Restart the backend and open http://localhost:8000/admin-web/.
FastAPI serves `admin-web/dist`; API requests use the same origin. No separate web server is required.
For a separately hosted build, set `VITE_API_URL` to the reachable API origin before building.
For Docker, mount the built `admin-web/dist` directory at `/admin-web/dist` in the API container.

## Features

- Administrator sign-in and sign-out; API role checks enforce ADMIN access.
- Driver directory with search and registration details.
- Create drivers with ID front/back and driving licence front photos, optional assistant, and an available bus assignment.
- Create buses with device identifiers and named routes; edit buses and routes.
- Writes go directly to the existing APIs and appear in Flutter after refreshing.

Routes follow the backend's current model: each bus stores a route name.
Photos accept JPEG/PNG up to 2 MB each and use the existing encrypted registration storage.
Access tokens remain in memory; reload requires signing in again. No passwords or photos are persisted in browser storage.
