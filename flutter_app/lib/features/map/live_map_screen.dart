import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../providers/auth_provider.dart';
import '../transport/transport_state.dart';

class LiveMapScreen extends ConsumerStatefulWidget {
  const LiveMapScreen({super.key, this.driver = true});
  final bool driver;
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
  List<LatLng> _route = [];
  List<Map<String, dynamic>> _stops = [];
  List<LatLng> _history = [];
  String _child = '';
  String _childStatus = '';
  int? _studentId;
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
    if (!kIsWeb && (defaultTargetPlatform == TargetPlatform.iOS ||
        defaultTargetPlatform == TargetPlatform.android)) {
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
      _poll?.cancel();
      final api = ref.read(apiClientProvider).dio;
      dynamic bus;
      if (widget.driver) {
        bus = (await api.get('/driver/bus')).data;
      } else {
        final children = (await api.get('/me/transport')).data as List;
        if (!mounted) return;
        if (children.isEmpty) {
          setState(
              () => _status = 'No children assigned. Contact your school.');
          return;
        }
        final index =
            ref.read(selectedChildProvider).clamp(0, children.length - 1);
        final child = children[index];
        _child = child['name'] as String;
        _studentId = child['id'] as int;
        if (child['bus_id'] == null) {
          setState(() =>
              _status = 'No bus assigned to $_child. Contact your school.');
          return;
        }
        bus = {'id': child['bus_id'], 'plate_no': child['plate_no']};
      }
      if (!mounted) return;
      setState(() {
        _busId = bus['id'] as int;
        _plate = bus['plate_no'] as String;
        _status = widget.driver
            ? 'Ready to share your phone location'
            : 'Loading $_child’s bus location…';
      });
      final route = (await api.get('/buses/$_busId/route')).data;
      if (!mounted) return;
      setState(() {
        _stops = (route['stops'] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        _route = _stops
            .map((e) => LatLng(
                (e['lat'] as num).toDouble(), (e['lng'] as num).toDouble()))
            .toList();
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
      if (_studentId != null) {
        final status = (await ref
                .read(apiClientProvider)
                .dio
                .get('/students/$_studentId/status'))
            .data;
        if (!mounted) return;
        setState(() => _childStatus = status['status'] == 'ON_BUS'
            ? 'Last boarding event: on bus'
            : 'No current boarding confirmation');
      }
      final history = (await ref
              .read(apiClientProvider)
              .dio
              .get('/buses/$_busId/route-history', queryParameters: {
        'from': DateTime.now()
            .toUtc()
            .subtract(const Duration(hours: 2))
            .toIso8601String(),
      }))
          .data;
      if (!mounted) return;
      setState(() => _history = (history['points'] as List)
          .map((e) => LatLng(
              (e['lat'] as num).toDouble(), (e['lng'] as num).toDouble()))
          .toList());
      final response = await ref
          .read(apiClientProvider)
          .dio
          .get('/buses/$_busId/live-location');
      if (!mounted || _sharing) return;
      final data = response.data;
      _showPoint(LatLng(
          (data['lat'] as num).toDouble(), (data['lng'] as num).toDouble()));
      final updated = DateTime.parse(data['server_time'] as String).toUtc();
      final stale = DateTime.now().toUtc().difference(updated) >
          const Duration(minutes: 2);
      setState(() => _status =
          '${stale ? "Bus location is stale" : "Bus location updated"} · ${updated.toLocal()}');
    } on DioException catch (e) {
      if (mounted && !_sharing) {
        setState(() => _status = e.response?.statusCode == 404
            ? (widget.driver
                ? 'No bus location yet. Start sharing to send your position.'
                : 'Waiting for the driver to share a location.')
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
                              'The map is unavailable in this build. Location updates are shown below.',
                              textAlign: TextAlign.center,
                            ),
                          ),
                        )
                      : GoogleMap(
                          initialCameraPosition: const CameraPosition(
                              target: LatLng(7.4863, 80.3647), zoom: 15),
                          onMapCreated: (controller) {
                            _map = controller;
                            if (_point != null) {
                              controller
                                  .moveCamera(CameraUpdate.newLatLng(_point!));
                            }
                          },
                          polylines: {
                            if (_route.isNotEmpty)
                              Polyline(
                                  polylineId: const PolylineId('sample'),
                                  points: _route,
                                  color: Colors.grey,
                                  patterns: [
                                    PatternItem.dash(12),
                                    PatternItem.gap(8)
                                  ]),
                            if (_history.isNotEmpty)
                              Polyline(
                                  polylineId: const PolylineId('recorded'),
                                  points: _history,
                                  color: Colors.blue,
                                  width: 5),
                          },
                          markers: {
                            for (var i = 0; i < _stops.length; i++)
                              Marker(
                                  markerId: MarkerId('stop$i'),
                                  position: _route[i],
                                  infoWindow: InfoWindow(
                                      title: _stops[i]['name'] as String),
                                  icon: BitmapDescriptor.defaultMarkerWithHue(
                                      BitmapDescriptor.hueGreen)),
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
                    if (_point != null)
                      Text(
                          'Bus coordinates: ${_point!.latitude.toStringAsFixed(5)}, ${_point!.longitude.toStringAsFixed(5)}'),
                    if (!widget.driver)
                      TextButton(
                          onPressed: _loadBus,
                          child: const Text('Refresh tracking')),
                    const SizedBox(height: 8),
                    if (!widget.driver)
                      Text('$_child · $_childStatus',
                          textAlign: TextAlign.center),
                    const Text(
                        'Grey: approximate sample school stops · Blue: recorded GPS trail',
                        textAlign: TextAlign.center),
                    if (widget.driver)
                      const Text(
                          'Keep this screen open during the trip. Sharing stops when you leave this screen or put the app in the background.',
                          textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    if (widget.driver)
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
