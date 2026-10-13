# School Bus Flutter UI

Parent and driver flows follow the blue, grey, rounded-card styling in the [Bus system Figma design](https://www.figma.com/design/CLFiBCm4xZrFY1TnocarbK/Bus-system?node-id=0-1).

Run `flutter pub get` and `flutter run` from this directory. The existing temporary sign-in bypass opens a role selector. Choose **Parent** to select a child, or **Bus driver** to open the driver dashboard. The back arrow on either dashboard returns to role selection.

Parent screens include child selection and creation, journey times, notifications, bus route preview, and driver/school profile sheets. Driver screens include a dashboard, route preview, attendance summary, searchable student list, student profiles, student creation, and SOS assistance options.

Transport data is sample data in `lib/features/transport/transport_state.dart`. Added children/students remain available for the current session only. Map artwork is a static Figma route preview; SOS options display an informational dialog and do not call or send an alert. The previous Google Maps placeholder is preserved in `live_map_screen.dart` for later integration. Role selection is a UI preview, not backend driver authorization.

The Figma detail-list and driver add-student frames could not be retrieved due to the account's MCP limit. These screens use the available form, profile, and dashboard styles. Placeholder content in the supplied designs has been replaced with sample details and controls.

Figma assets are bundled under `assets/figma/`. Roboto is bundled under `assets/fonts/` with its license. SVG filter shadows are unsupported by Flutter's SVG renderer; card shadows are rendered with Flutter decorations.

Validation:

```sh
flutter test
flutter analyze --no-fatal-infos
```

The analyzer reports existing informational style lints in child detail and settings screens. To generate phone-sized screenshots of the implemented flows:

```sh
flutter test test/ui_preview_test.dart --dart-define=CAPTURE_UI=true
```

Previews are written to `build/ui-preview/`. Widget tests cover parent selection/switching and profiles, driver navigation and student search, form validation and shared session state, and home layouts at 320, 402, and 600 pixels.
