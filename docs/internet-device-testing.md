# Phones on different networks

An APK built with a Mac's private Wi-Fi IP only works on that local network.
Changing server settings does not update the URL compiled into an installed app.
Build and install a replacement using the ngrok HTTPS origin.

From the repository root, leave the existing API running on port 8000. If it
is stopped, start it in a terminal:

```sh
cd backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

This retains the existing SQLite database when run from `backend/`. Do not run
another API on port 8000 if the existing process is already listening there.

Install ngrok and configure your account token locally (never commit or share it):

```sh
brew install --cask ngrok
ngrok config add-authtoken YOUR_TOKEN_FROM_NGROK_DASHBOARD
ngrok http http://127.0.0.1:8000
```

Get the token from https://dashboard.ngrok.com/get-started/your-authtoken.
Leave ngrok running and copy its HTTPS Forwarding URL. In another terminal,
from the repository root, substitute that URL:

```sh
bash scripts/build-internet-apk.sh https://YOUR-DOMAIN.ngrok-free.app
```

Install `flutter_app/build/app/outputs/flutter-apk/app-release.apk` on the remote
Android phone, replacing the older build. This project currently signs release
APKs with its debug certificate for testing. If Android reports a certificate
mismatch, uninstalling the old app removes its local data; do that only after
confirming that loss is acceptable.

For an attached iPhone with signing configured in Xcode:

```sh
cd flutter_app
flutter devices
flutter run --release -d IPHONE_DEVICE_ID --dart-define=API_BASE_URL=https://YOUR-DOMAIN.ngrok-free.app
```

Keep the Mac plugged in, awake, and online. In another terminal:

```sh
caffeinate -is
```

Keep the lid open. Stop caffeinate or ngrok with Ctrl+C when finished. Restart
ngrok with the same command; if its URL changes, rebuild and reinstall both apps.
The public origin also supports the existing native WebSocket endpoint using
`wss://`; Flutter currently receives locations through REST polling.

## Verify

1. On a phone with Wi-Fi disabled, open `https://YOUR-DOMAIN.ngrok-free.app/health`.
   After any ngrok browser confirmation, expect `status: ok`.
2. Install the replacement build; sign in as the driver using `driver@example.com`.
3. Open the driver's live map, grant location access, and start sharing. Keep the
   screen open and unlocked; background sharing is not implemented.
4. On the other phone, use the same public URL and sign in as `parent@example.com`.
   Open its assigned child's live map. Both accounts are linked to BUS-24.
5. Move the driver phone more than 10 metres outdoors. The viewer polls every five
   seconds; GPS acquisition and network latency add delay.
6. Disconnect and restore the viewer's internet. Polling should recover. Driver
   uploads retry on subsequent GPS fixes; offline fixes are not queued.

The tunnel exposes this API publicly, including its authenticated admin routes
and API docs. Existing demo credentials and default backend secrets are suitable
only for isolated local development; replace them and restrict public routes
before sharing a tunnel containing sensitive data. Do not expose PostgreSQL or
Redis ports. Ngrok's local request inspector may contain sensitive request data.
This setup depends on Mac uptime, home internet and ngrok account limits.

Official setup: https://ngrok.com/download/mac-os
