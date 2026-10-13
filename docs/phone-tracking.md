# Driver phone tracking

The driver home page opens a Google Map through **Live bus location → View**.
Tap **Start sharing**, grant location permission, and keep the map screen open.
The phone streams high-accuracy positions after moving 10 metres and uploads
at most once every five seconds. The initial GPS fix is also uploaded.
**Stop sharing**, leaving the map screen, or backgrounding the app stops tracking.
This is foreground tracking; it does not continue with the phone locked.

## Setup

1. Create/enable a Google Maps Platform key with Maps SDK for iOS enabled and
   billing configured. Restrict the key to the application's bundle identifier.
2. In Xcode, add a user-defined build setting named `GOOGLE_MAPS_API_KEY` to the
   Runner target for the build configurations you use. Its value is your key.
   Info.plist passes this setting to AppDelegate. Do not commit the key.
   The backend's similarly named environment variable does not configure the app.
3. Run `flutter pub get` and install iOS pods as usual.
4. Configure an ACTIVE driver record through the existing driver management API,
   linking `user_id` to a DRIVER account and `bus_id` to the bus being driven.
5. Launch with `flutter run --dart-define=API_BASE_URL=https://your-api-host`.
   On a physical phone, localhost refers to the phone; use a reachable API host.

This repository currently includes iOS but no Android runner. When adding Android,
configure the Google Maps Android API key and ACCESS_FINE_LOCATION /
ACCESS_COARSE_LOCATION permissions following the plugin documentation.

## API and behavior

- `GET /driver/bus`: returns the authenticated driver's active bus assignment.
- `POST /driver/location`: accepts lat, lng, GPS timestamp, optional speed (m/s),
  and heading (degrees). The server determines the bus from the driver's account;
  clients cannot choose a different bus ID. Invalid coordinates are rejected.
- Existing `GET /buses/{bus_id}/live-location`, route history, and WebSocket feeds
  receive these positions through the same location storage as hardware GPS.

When sharing is off, the driver map polls the latest saved bus position every
five seconds and displays its timestamp. A saved position is not proof that the
bus is currently moving. Failed uploads show an error and subsequent GPS fixes
retry; offline positions are not queued. Existing parent locator screens still
use their sample route UI; this change connects the driver screen.

Verify the map tiles, permission prompts, movement, stop/background behavior,
and network failures on a physical phone before using it during a trip.

References: https://pub.dev/packages/geolocator/versions/13.0.4 and
https://pub.dev/packages/google_maps_flutter
