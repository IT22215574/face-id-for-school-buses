import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

class GpsPolicy {
  const GpsPolicy(
      {this.interval = const Duration(seconds: 5),
      this.distance = 10,
      this.heartbeat = const Duration(seconds: 60),
      this.maximumAccuracy = 100});
  final Duration interval, heartbeat;
  final int distance;
  final double maximumAccuracy;

  bool shouldUpload(
      Position point, Position? previous, DateTime? sentAt, DateTime now) {
    if (!point.latitude.isFinite ||
        !point.longitude.isFinite ||
        point.latitude.abs() > 90 ||
        point.longitude.abs() > 180 ||
        !point.accuracy.isFinite ||
        point.accuracy < 0 ||
        point.accuracy > maximumAccuracy ||
        now.difference(point.timestamp).abs() > const Duration(minutes: 2)) {
      return false;
    }
    if (previous == null || sentAt == null) return true;
    final elapsed = now.difference(sentAt);
    return elapsed >= interval &&
        (elapsed >= heartbeat ||
            Geolocator.distanceBetween(previous.latitude, previous.longitude,
                    point.latitude, point.longitude) >=
                distance);
  }

  LocationSettings settings(bool background) {
    if (defaultTargetPlatform == TargetPlatform.android) {
      return AndroidSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 0,
          intervalDuration: interval,
          foregroundNotificationConfig: background
              ? const ForegroundNotificationConfig(
                  notificationTitle: 'Location sharing active',
                  notificationText:
                      'Your selected contacts can see your location. Open the app to stop.',
                  enableWakeLock: true)
              : null);
    }
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      return AppleSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 0,
          activityType: ActivityType.automotiveNavigation,
          pauseLocationUpdatesAutomatically: false,
          allowBackgroundLocationUpdates: background,
          showBackgroundLocationIndicator: background);
    }
    return const LocationSettings(accuracy: LocationAccuracy.high);
  }
}
