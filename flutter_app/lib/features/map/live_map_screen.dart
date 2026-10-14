import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../providers/auth_provider.dart';

class LiveMapScreen extends ConsumerStatefulWidget {
  const LiveMapScreen({super.key});
  @override
  ConsumerState<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends ConsumerState<LiveMapScreen>
    with WidgetsBindingObserver {
  GoogleMapController? _map;
  StreamSubscription<Position>? _positions;
  Timer? _poll;
  LatLng? _point;
  int? _busId;
  String _plate = '';
  String _status = 'Loading your assigned bus…';
  bool _sharing = false, _busy = false, _uploading = false, _reading = false;
  int _session = 0;
  DateTime? _lastUpload;
  bool _mapsReady = false;
  bool _checkingMaps = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkMapsConfiguration();
    _loadBus();
  }

  Future<void> _checkMapsConfiguration() async {
    var ready = true;
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.iOS) {
      try {
        ready = await const MethodChannel('school_bus/maps_configuration')
                .invokeMethod<bool>('isConfigured') ??
            false;
      } on PlatformException {
        ready = false;
      } on MissingPluginException {
        ready = false;
      }
    }
    if (!mounted) return;
    setState(() {
      _mapsReady = ready;
      _checkingMaps = false;
    });
  }

  Future<void> _loadBus() async {
    try {
      final response = await ref.read(apiClientProvider).dio.get('/driver/bus');
      if (!mounted) return;
      setState(() {
        _busId = response.data['id'] as int;
        _plate = response.data['plate_no'] as String;
        _status = 'Ready to share your phone location';
      });
      await _readLocation();
      if (mounted) {
        _poll =
            Timer.periodic(const Duration(seconds: 5), (_) => _readLocation());
      }
    } on DioException catch (e) {
      if (mounted) setState(() => _status = _error(e));
    }
  }

  String _error(DioException e) {
    final data = e.response?.data;
    return data is Map && data['detail'] is String
        ? data['detail'] as String
        : 'Cannot reach the server. Check your connection and try again.';
  }

  Future<void> _readLocation() async {
    if (_busId == null || _sharing || _reading) return;
    _reading = true;
    try {
      final response = await ref
          .read(apiClientProvider)
          .dio
          .get('/buses/$_busId/live-location');
      if (!mounted || _sharing) return;
      final data = response.data;
      _showPoint(LatLng(
          (data['lat'] as num).toDouble(), (data['lng'] as num).toDouble()));
      setState(() => _status = 'Last bus update: ${data['server_time']}');
    } on DioException catch (e) {
      if (mounted && !_sharing) {
        setState(() => _status = e.response?.statusCode == 404
            ? 'No bus location yet. Start sharing to send your position.'
            : _error(e));
      }
    } finally {
      _reading = false;
    }
  }

  void _showPoint(LatLng point) {
    setState(() => _point = point);
    _map?.animateCamera(CameraUpdate.newLatLng(point));
  }

  Future<void> _start() async {
    final session = ++_session;
    setState(() {
      _busy = true;
      _status = 'Checking GPS permission…';
    });
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        throw Exception(
            'Enable location services on your phone, then try again.');
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever) {
        throw Exception(
            'Location permission is blocked. Enable it in phone settings.');
      }
      if (permission != LocationPermission.whileInUse &&
          permission != LocationPermission.always) {
        throw Exception(
            'Location permission is needed to share your bus position.');
      }
      if (!mounted || session != _session) return;
      setState(() {
        _sharing = true;
        _status = 'Waiting for GPS…';
      });
      _lastUpload = null;
      _positions = Geolocator.getPositionStream(
        locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.high, distanceFilter: 10),
      ).listen((position) => _send(position, session), onError: (Object error) {
        if (mounted) {
          _stop();
          setState(() => _status =
              'GPS unavailable. Check location services and restart sharing.');
        }
      });
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 20)),
      );
      await _send(position, session);
    } catch (e) {
      if (mounted && session == _session) {
        _stop();
        setState(() => _status = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send(Position position, int session) async {
    if (!mounted || !_sharing || session != _session || _uploading) return;
    _showPoint(LatLng(position.latitude, position.longitude));
    if (_lastUpload != null &&
        DateTime.now().difference(_lastUpload!) < const Duration(seconds: 5)) {
      return;
    }
    _uploading = true;
    try {
      await ref.read(apiClientProvider).dio.post('/driver/location', data: {
        'lat': position.latitude,
        'lng': position.longitude,
        'speed': position.speed >= 0 ? position.speed : null,
        'heading': position.heading >= 0 && position.heading < 360
            ? position.heading
            : null,
        'gps_time': position.timestamp.toUtc().toIso8601String(),
      });
      if (mounted && _sharing && session == _session) {
        _lastUpload = DateTime.now();
        setState(() =>
            _status = 'Sharing · last sent ${TimeOfDay.now().format(context)}');
      }
    } on DioException catch (e) {
      if (mounted && session == _session) {
        if (e.response?.statusCode == 401 || e.response?.statusCode == 403) {
          _stop();
        }
        setState(() => _status = 'Location not sent: ${_error(e)}');
      }
    } finally {
      _uploading = false;
    }
  }

  void _stop() {
    ++_session;
    _positions?.cancel();
    _positions = null;
    setState(() {
      _sharing = false;
      _busy = false;
      _status = 'Sharing stopped. Last saved location remains visible.';
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if ((state == AppLifecycleState.paused ||
            state == AppLifecycleState.hidden ||
            state == AppLifecycleState.detached) &&
        (_sharing || _busy)) {
      _stop();
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title:
                Text(_plate.isEmpty ? 'Live Bus Map' : 'Live Map · $_plate')),
        body: Column(children: [
          Expanded(
              child: _checkingMaps
                  ? const Center(child: CircularProgressIndicator())
                  : !_mapsReady
                      ? const Center(
                          child: Padding(
                            padding: EdgeInsets.all(24),
                            child: Text(
                              'The map is unavailable in this build. You can still share your bus location below.',
                              textAlign: TextAlign.center,
                            ),
                          ),
                        )
                      : GoogleMap(
                          initialCameraPosition: const CameraPosition(
                              target: LatLng(6.9271, 79.8612), zoom: 15),
                          onMapCreated: (controller) {
                            _map = controller;
                            if (_point != null) {
                              controller
                                  .moveCamera(CameraUpdate.newLatLng(_point!));
                            }
                          },
                          markers: {
                            if (_point != null)
                              Marker(
                                  markerId: const MarkerId('bus'),
                                  position: _point!,
                                  infoWindow: InfoWindow(title: _plate))
                          },
                        )),
          SafeArea(
              top: false,
              child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(children: [
                    Text(_status, textAlign: TextAlign.center),
                    const SizedBox(height: 8),
                    const Text(
                        'Keep this screen open during the trip. Sharing stops when you leave this screen or put the app in the background.',
                        textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: _sharing
                          ? _stop
                          : _busy
                              ? null
                              : _busId == null
                                  ? _loadBus
                                  : _start,
                      icon: Icon(_sharing ? Icons.stop : Icons.location_on),
                      label: Text(_sharing
                          ? 'Stop sharing'
                          : _busy
                              ? 'Starting…'
                              : _busId == null
                                  ? 'Retry bus assignment'
                                  : 'Start sharing'),
                    ),
                  ]))),
        ]),
      );

  @override
  void dispose() {
    ++_session;
    WidgetsBinding.instance.removeObserver(this);
    _positions?.cancel();
    _poll?.cancel();
    _map?.dispose();
    super.dispose();
  }
}
