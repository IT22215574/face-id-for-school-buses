import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:school_bus_parent_app/features/tracking/gps_policy.dart';

Position fix(DateTime time, {double lat = 7, double accuracy = 5}) => Position(
    latitude: lat,
    longitude: 80,
    timestamp: time,
    accuracy: accuracy,
    altitude: 0,
    altitudeAccuracy: 0,
    heading: 0,
    headingAccuracy: 0,
    speed: 0,
    speedAccuracy: 0);

void main() {
  const policy = GpsPolicy();
  final now = DateTime.utc(2026, 10, 19);
  test('first accurate fresh fix uploads; inaccurate and old fixes do not', () {
    expect(policy.shouldUpload(fix(now), null, null, now), isTrue);
    expect(
        policy.shouldUpload(fix(now, accuracy: 101), null, null, now), isFalse);
    expect(
        policy.shouldUpload(
            fix(now.subtract(const Duration(minutes: 3))), null, null, now),
        isFalse);
    expect(policy.shouldUpload(fix(now, lat: double.nan), null, null, now),
        isFalse);
  });
  test('movement respects minimum interval and stationary heartbeat', () {
    final previous = fix(now);
    expect(
        policy.shouldUpload(fix(now, lat: 7.01), previous, now,
            now.add(const Duration(seconds: 4))),
        isFalse);
    expect(
        policy.shouldUpload(fix(now, lat: 7.01), previous, now,
            now.add(const Duration(seconds: 5))),
        isTrue);
    expect(
        policy.shouldUpload(
            fix(now), previous, now, now.add(const Duration(seconds: 5))),
        isFalse);
    expect(
        policy.shouldUpload(
            fix(now), previous, now, now.add(const Duration(seconds: 60))),
        isTrue);
  });
}
