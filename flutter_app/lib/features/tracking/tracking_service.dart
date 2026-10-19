import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../../core/api_client.dart';
import '../../providers/auth_provider.dart';
import 'gps_policy.dart';

final trackingProvider = ChangeNotifierProvider<TrackingService>((ref) {
  final service = TrackingService(ref.read(apiClientProvider));
  ref.listen(authStateProvider, (_, role) {
    if (role == null) unawaited(service.close());
  });
  return service;
});

class TrackedPoint {
  TrackedPoint(this.lat, this.lng, this.updatedAt);
  final double lat, lng;
  final DateTime updatedAt;
  static TrackedPoint? parse(Object? value) {
    if (value is! Map ||
        value['lat'] is! num ||
        value['lng'] is! num ||
        value['updatedAt'] is! num) {
      return null;
    }
    final lat = (value['lat'] as num).toDouble();
    final lng = (value['lng'] as num).toDouble();
    if (!lat.isFinite || !lng.isFinite || lat.abs() > 90 || lng.abs() > 180) {
      return null;
    }
    return TrackedPoint(
        lat,
        lng,
        DateTime.fromMillisecondsSinceEpoch(
            (value['updatedAt'] as num).toInt()));
  }
}

class TrackingService extends ChangeNotifier with WidgetsBindingObserver {
  TrackingService(this.api) {
    WidgetsBinding.instance.addObserver(this);
  }
  final ApiClient api;
  FirebaseAuth? _auth;
  FirebaseDatabase? _database;
  StreamSubscription<DatabaseEvent>? _following, _grants, _connection;
  final Map<String, StreamSubscription<DatabaseEvent>> _devices = {};
  StreamSubscription<Position>? _gps;
  final points = <String, TrackedPoint>{};
  Set<String> viewers = {};
  String? uid;
  String status = 'Connect to enable private location sharing.';
  bool sharing = false, background = false, busy = false, _uploading = false;
  bool _disposed = false;
  int _session = 0;
  Position? _last;
  DateTime? _sent;
  GpsPolicy policy = const GpsPolicy();

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void _error(Object error) {
    status = error is FirebaseException
        ? '${error.code}: ${error.message ?? "Location service unavailable"}'
        : '$error';
    _notify();
  }

  Future<void> connect() async {
    if (busy || uid != null) return;
    busy = true;
    _notify();
    final session = _session;
    try {
      const project = String.fromEnvironment('FIREBASE_PROJECT_ID');
      if (project.isEmpty) {
        throw StateError('Configure Firebase using the tracking setup guide.');
      }
      final app = Firebase.apps.isEmpty
          ? await Firebase.initializeApp(
              options: const FirebaseOptions(
              apiKey: String.fromEnvironment('FIREBASE_API_KEY'),
              appId: String.fromEnvironment('FIREBASE_APP_ID'),
              messagingSenderId:
                  String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID'),
              projectId: project,
              databaseURL: String.fromEnvironment('FIREBASE_DATABASE_URL'),
            ))
          : Firebase.app();
      final response = await api.dio.post('/auth/firebase-token');
      if (_disposed || session != _session) return;
      _auth = FirebaseAuth.instanceFor(app: app);
      await _auth!.signInWithCustomToken(response.data['token'] as String);
      if (_disposed || session != _session) {
        await _auth!.signOut();
        return;
      }
      uid = _auth!.currentUser!.uid;
      _database = FirebaseDatabase.instanceFor(
          app: app,
          databaseURL: const String.fromEnvironment('FIREBASE_DATABASE_URL'));
      // Never persist GPS uploads across process restarts or sign-ins.
      _connection = _database!.ref('.info/connected').onValue.listen((event) {
        if (event.snapshot.value != true) {
          status =
              'Offline. Locations may be stale; GPS uploads will resume with fresh fixes.';
        } else if (!sharing) {
          status = 'Connected. Share only with people you choose.';
        }
        _notify();
      }, onError: _error);
      _following = _database!.ref('following/$uid').onValue.listen((event) {
        final data = event.snapshot.value;
        final ids = data is Map ? data.keys.cast<String>().toSet() : <String>{};
        for (final id in _devices.keys.toList()) {
          if (!ids.contains(id)) {
            _devices.remove(id)?.cancel();
            points.remove(id);
          }
        }
        for (final id in ids) {
          _devices.putIfAbsent(
              id,
              () => _database!.ref('locations/$id').onValue.listen((event) {
                    final point = TrackedPoint.parse(event.snapshot.value);
                    if (point == null) {
                      points.remove(id);
                    } else {
                      points[id] = point;
                    }
                    _notify();
                  }, onError: (Object error) {
                    points.remove(id);
                    _error(error);
                  }));
        }
        _notify();
      }, onError: _error);
      _grants = _database!.ref('shares/$uid').onValue.listen((event) {
        final data = event.snapshot.value;
        viewers = data is Map ? data.keys.cast<String>().toSet() : {};
        _notify();
      }, onError: _error);
      status = 'Connected. Share only with people you choose.';
    } catch (error) {
      uid = null;
      _error(error);
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> grant(String viewer, bool enabled) async {
    if (uid == null ||
        !RegExp(r'^account_[1-9][0-9]*$').hasMatch(viewer) ||
        viewer == uid) {
      throw StateError('Enter another account’s sharing ID (account_123).');
    }
    await _database!.ref().update({
      'shares/$uid/$viewer': enabled ? true : null,
      'following/$viewer/$uid': enabled ? true : null,
    });
  }

  Future<void> start({required bool inBackground}) async {
    if (uid == null || sharing || busy) return;
    busy = true;
    _notify();
    final session = ++_session;
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        throw StateError('Enable phone location services and try again.');
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever) {
        throw StateError(
            'Location permission is blocked. Open app settings to allow it.');
      }
      if (permission != LocationPermission.always &&
          permission != LocationPermission.whileInUse) {
        throw StateError('Location permission is required.');
      }
      if (inBackground &&
          defaultTargetPlatform == TargetPlatform.iOS &&
          permission != LocationPermission.always) {
        throw StateError(
            'Allow Always location access in phone settings for background sharing.');
      }
      if (inBackground && defaultTargetPlatform == TargetPlatform.android) {
        await FlutterLocalNotificationsPlugin()
            .resolvePlatformSpecificImplementation<
                AndroidFlutterLocalNotificationsPlugin>()
            ?.requestNotificationsPermission();
      }
      if (_disposed || session != _session) return;
      background = inBackground;
      sharing = true;
      _last = null;
      _sent = null;
      status = 'Waiting for GPS…';
      _gps = Geolocator.getPositionStream(
              locationSettings: policy.settings(background))
          .listen((position) => unawaited(_send(position, session)),
              onError: (Object error) {
        stop();
        _error(error);
      });
    } catch (error) {
      _error(error);
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> _send(Position position, int session) async {
    if (!sharing || session != _session || _uploading) return;
    if (!policy.shouldUpload(position, null, null, DateTime.now())) return;
    points[uid!] =
        TrackedPoint(position.latitude, position.longitude, position.timestamp);
    _notify();
    final now = DateTime.now();
    if (!policy.shouldUpload(position, _last, _sent, now)) return;
    _uploading = true;
    try {
      // Do not queue old GPS positions while offline.
      final connected = await _database!
          .ref('.info/connected')
          .get()
          .timeout(const Duration(seconds: 3));
      if (connected.value != true) {
        throw StateError(
            'Offline. Waiting for a fresh GPS fix after reconnecting.');
      }
      if (!sharing || session != _session) return;
      await _database!.ref('locations/$uid').set({
        'lat': position.latitude,
        'lng': position.longitude,
        'accuracy': position.accuracy,
        if (position.speed.isFinite && position.speed >= 0)
          'speed': position.speed,
        if (position.heading.isFinite &&
            position.heading >= 0 &&
            position.heading < 360)
          'heading': position.heading,
        'timestamp': position.timestamp.millisecondsSinceEpoch,
        'updatedAt': ServerValue.timestamp,
      }).timeout(const Duration(seconds: 10));
      if (session != _session) return;
      _last = position;
      _sent = now;
      status =
          'Sharing location${background ? " in background" : " while app is open"}';
      _notify();
    } catch (error) {
      await _database?.purgeOutstandingWrites();
      if (session == _session) _error(error);
    } finally {
      _uploading = false;
    }
  }

  void stop() {
    ++_session;
    _gps?.cancel();
    _gps = null;
    sharing = false;
    if (_database != null) unawaited(_database!.purgeOutstandingWrites());
    status = 'Sharing stopped. Last location remains until you delete it.';
    _notify();
  }

  Future<void> deleteLocation() async {
    stop();
    if (uid != null) {
      await _database!.ref('locations/$uid').remove();
      points.remove(uid);
      _notify();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!background &&
        (state == AppLifecycleState.paused ||
            state == AppLifecycleState.hidden)) {
      stop();
    }
  }

  Future<void> close() async {
    stop();
    await _following?.cancel();
    await _grants?.cancel();
    await _connection?.cancel();
    for (final subscription in _devices.values) {
      await subscription.cancel();
    }
    _devices.clear();
    points.clear();
    viewers = {};
    uid = null;
    await _auth?.signOut();
    _notify();
  }

  @override
  void dispose() {
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    unawaited(close());
    super.dispose();
  }
}
