# Real-time device tracking

The existing project uses Riverpod, FastAPI JWT login, SQL bus assignments, and a
Google Maps bus screen with an OpenStreetMap fallback. These remain in place.
Open **Shared devices** (the share-location icon in the Live Map app bar) for
Firebase location sharing. The backend exchanges the authenticated account for a
Firebase custom token; no separate Firebase password or anonymous login is used.
The sharing ID is `account_<SQL account ID>` and is displayed after connecting.

## Configure

1. Enable Maps SDK for Android and Maps SDK for iOS in your Google Cloud project
   with billing. Use different keys restricted to the actual Android application
   ID + release signing certificate SHA-1 and iOS bundle identifier, and restrict
   each key to its platform's Maps SDK. Mobile keys are embedded in binaries:
   source exclusion alone does not make them secret.
2. Android already reads `GOOGLE_MAPS_API_KEY` from a Gradle property or environment
   variable. Put it in your private `~/.gradle/gradle.properties`, or inject it in
   CI. For iOS create ignored `flutter_app/ios/Flutter/LocalKeys.xcconfig` containing
   `GOOGLE_MAPS_API_KEY = your_ios_key`; Debug and Release include this file.
3. Register the Android and iOS apps in the same Firebase project. Create a
   Realtime Database. Copy `flutter_app/config/tracking.example.json` to
   `tracking.android.json` and `tracking.ios.json` in that directory and fill in
   each registered app's Firebase options. These local files are ignored. The
   Firebase API key is a client identifier; database access is enforced by rules.
   The database URL must be the actual regional instance URL.
4. On the FastAPI server set `FIREBASE_TRACKING_ENABLED=true`, `FCM_PROJECT_ID`,
   and `FCM_CREDENTIALS_JSON` to a valid service account JSON for that same
   project. Keep service credentials on the server only. The named Admin app
   `tracking` does not interfere with the existing notification Admin app.
5. Deploy the included deny-by-default rules from the repository root:
   `firebase deploy --only database --project YOUR_PROJECT_ID`.
   This requires Firebase CLI login and database management access. Rules have
   been supplied locally; this task does not deploy to your cloud account.
6. Run from `flutter_app`:
   `flutter run --dart-define-from-file=config/tracking.android.json`
   (use the iOS file for iOS). For iOS run `flutter pub get` and `pod install`
   in `ios` after adding dependencies. Firebase initializes lazily when the user
   connects; the existing screens still work without Firebase configuration.

## Sharing and access

Connect, copy your sharing ID, and enter a recipient's sharing ID to grant them
access to your location. Only the owner can grant or revoke access. A recipient
cannot grant themselves access. Grant/revoke atomically updates the owner's
`shares` and recipient's `following` index. Receivers subscribe to individual
location paths; there is no public location list or broad locations read.
Revoking access removes the receiver's subscription and its marker. A last known
location may remain in a person's memory or screenshots after access is revoked.

Start sharing separately from granting access. An account can share from one
phone at a time: another phone signed into the same account overwrites that
account's position. Multiple distinct accounts have independent markers.
Choose a device in the dropdown to follow it; Stop following restores free
camera movement. Markers interpolate over 650 ms, including longitude wrapping.
Locations older than two minutes are dimmed and labeled stale. The owner marker
is blue; granted devices are red. Stop sharing halts updates; Delete my last
location removes the saved location. Logout stops GPS, cancels subscriptions,
clears displayed coordinates, and signs out of Firebase.

## GPS and background behavior

`GpsPolicy` defaults to an Android requested interval of five seconds, minimum
movement of 10 meters, a stationary heartbeat of 60 seconds, and maximum accepted
accuracy of 100 meters. It rejects invalid/stale fixes and limits uploads to at
most one per five seconds. The stream requests all fixes so stationary heartbeat
uploads can occur when the OS delivers fixes. Configure the provider's policy
before starting to change these values. iOS controls location delivery cadence;
five seconds is an upload minimum, not a guaranteed location timer.

Background mode is explicitly opt-in. On Android a location foreground service
is started while the app is visible, with an ongoing notification, notification
permission request, and wake lock. The geolocator Android plugin supplies the
manifest service with `foregroundServiceType="location"`; the app declares the
foreground-service permissions. This uses foreground-service access rather than
`ACCESS_BACKGROUND_LOCATION`: it does not start GPS from the background or after
reboot. Android notification denial may hide the drawer notification; tracking
can still appear in the system's active apps view. OEM battery restrictions,
battery saver, force-stop, and process termination can interrupt delivery. Ask
users to review their device battery settings if tracking is interrupted; no
battery-exemption prompt is forced.

On iOS the location background mode and Always usage description are configured.
The app requires Always permission for its background option; if needed select
Always in system App Settings after granting initial access. Background location
updates use automotive activity, disable automatic pausing, and show the system
location indicator. Confirm the Location updates capability in Xcode before
release. iOS may defer or suspend updates, and force-quit/termination does not
have a guaranteed restart. There is no boot restart or terminated-app tracking.
The shared tracking service survives navigation away from its screen while the
user remains logged in; return to Shared devices to stop it. Foreground mode
stops when the app backgrounds. The original driver bus screen continues its
existing screen-bound foreground tracking behavior.

Uploads include coordinates, accuracy, GPS timestamp, optional speed in m/s,
optional heading in degrees, and server update time. Firebase disk persistence
is left disabled (the SDK default). Connectivity is checked before each write;
failed/timed-out pending writes are purged instead of building a GPS backlog.
A later fresh fix retries naturally. An already acknowledged write cannot be
retracted by Stop. Permission and stream errors are displayed; settings buttons
open location/app settings. Maps SDK key or billing failures after native map
creation can produce blank tiles; check native device logs and Cloud key/API
configuration, since the plugin has no universal tile-authentication error event.

## Validation before release

Use two real devices with separate existing accounts. Grant, start, receive,
follow, revoke, delete, and logout; verify unauthorized account reads/writes fail.
Test denied/permanently denied permissions, GPS disabled, airplane mode/reconnect,
stationary fixes, screen lock, backgrounding, notification denial, and battery
saver on supported Android/iOS releases. In Firebase Emulator rules tests verify
anonymous denial, owner-only writes, recipient read denial before grant and
after revocation, and malformed payload rejection. Emulator/device testing still
requires the configured environment; it has not been substituted by widget tests.

References:
- https://firebase.google.com/docs/auth/flutter/custom-auth
- https://firebase.google.com/docs/database/security/rules-conditions
- https://pub.dev/packages/geolocator/versions/13.0.4
