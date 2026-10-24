import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:latlong2/latlong.dart' as geo;
import 'testing_map.dart';
import '../tracking/shared_devices_screen.dart';
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
  Timer? _poll, _detailsPoll, _statusClock;
  bool _followBus = true;
  int _recenterSignal = 0;
  DateTime? _locationUpdatedAt;
  bool _locationError = false;
  bool _readingDetails = false;
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
    _statusClock = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() {});
    });
    _checkMapsConfiguration();
    _loadBus();
  }

  Future<void> _checkMapsConfiguration() async {
    var ready = true;
    if (!kIsWeb &&
        (defaultTargetPlatform == TargetPlatform.iOS ||
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
      _detailsPoll?.cancel();
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
      // Begin GPS polling before optional route/boarding details are loaded.
      _poll =
          Timer.periodic(const Duration(seconds: 5), (_) => _readLocation());
      _detailsPoll =
          Timer.periodic(const Duration(seconds: 30), (_) => _refreshDetails());
      await Future.wait([_readLocation(), _readRoute(), _refreshDetails()]);
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
      final time = DateTime.parse(data['server_time'] as String);
      // SQLite returns UTC timestamps without a zone suffix.
      final updated = time.isUtc
          ? time
          : DateTime.utc(time.year, time.month, time.day, time.hour,
              time.minute, time.second, time.millisecond, time.microsecond);
      _locationUpdatedAt = updated;
      _locationError = false;
      final stale = DateTime.now().toUtc().difference(updated) >
          const Duration(minutes: 2);
      setState(() => _status =
          '${stale ? "Bus location is stale" : "Bus location updated"} · ${updated.toLocal()}');
    } on DioException catch (e) {
      if (mounted && !_sharing) {
        _locationError = e.response?.statusCode != 404;
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

  Future<void> _readRoute() async {
    final busId = _busId;
    if (busId == null) return;
    try {
      final route =
          (await ref.read(apiClientProvider).dio.get('/buses/$busId/route'))
              .data;
      if (!mounted || busId != _busId) return;
      setState(() {
        _stops = (route['stops'] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        _route = _stops
            .map((e) => LatLng(
                (e['lat'] as num).toDouble(), (e['lng'] as num).toDouble()))
            .toList();
      });
    } on DioException {
      // The bus marker remains available when route details fail.
    }
  }

  Future<void> _refreshDetails() async {
    if (_readingDetails) return;
    _readingDetails = true;
    try {
      await _readDetails();
    } finally {
      _readingDetails = false;
    }
  }

  Future<void> _readDetails() async {
    if (_studentId != null) {
      try {
        final status = (await ref
                .read(apiClientProvider)
                .dio
                .get('/students/$_studentId/status'))
            .data;
        if (!mounted) return;
        setState(() => _childStatus = status['status'] == 'ON_BUS'
            ? 'Last boarding event: on bus'
            : 'No current boarding confirmation');
      } on DioException {
        if (mounted) {
          setState(() => _childStatus = 'Boarding status unavailable');
        }
      }
    }
    if (_busId == null) return;
    try {
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
    } on DioException {
      // History is optional; a missing trail must not hide the live position.
    }
  }

  void _showPoint(LatLng point) {
    setState(() => _point = point);
    if (_followBus) _map?.animateCamera(CameraUpdate.newLatLng(point));
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
        'accuracy_m': position.accuracy,
      });
      if (mounted && _sharing && session == _session) {
        _lastUpload = DateTime.now();
        _locationUpdatedAt = _lastUpload;
        _locationError = false;
        setState(() =>
            _status = 'Sharing · last sent ${TimeOfDay.now().format(context)}');
      }
    } on DioException catch (e) {
      if (mounted && session == _session) {
        _locationError = true;
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

  void _follow() {
    if (_point == null) return;
    setState(() {
      _followBus = true;
      ++_recenterSignal;
    });
    _map?.animateCamera(CameraUpdate.newLatLng(_point!));
  }

  String get _ageLabel {
    final updated = _locationUpdatedAt;
    if (updated == null) return 'Waiting for the first GPS update';
    final age = DateTime.now().toUtc().difference(updated.toUtc());
    if (age.inSeconds < 30) return 'Updated just now';
    if (age.inMinutes < 1) return 'Updated less than a minute ago';
    if (age.inHours < 1) return 'Updated ${age.inMinutes} min ago';
    if (age.inDays < 1) return 'Updated ${age.inHours} hr ago';
    return 'Updated ${age.inDays} days ago';
  }

  Widget _mapView() => _checkingMaps
      ? const Center(child: CircularProgressIndicator())
      : !_mapsReady
          ? TestingMap(
              point: _point == null
                  ? null
                  : geo.LatLng(_point!.latitude, _point!.longitude),
              route: _route
                  .map((p) => geo.LatLng(p.latitude, p.longitude))
                  .toList(),
              history: _history
                  .map((p) => geo.LatLng(p.latitude, p.longitude))
                  .toList(),
              stopNames: _stops.map((s) => s['name'] as String).toList(),
              plate: _plate,
              followBus: _followBus,
              showRecenter: false,
              recenterSignal: _recenterSignal,
            )
          : GoogleMap(
              mapToolbarEnabled: false,
              zoomControlsEnabled: false,
              initialCameraPosition: const CameraPosition(
                  target: LatLng(7.4863, 80.3647), zoom: 15),
              onMapCreated: (controller) {
                _map = controller;
                if (_point != null) {
                  controller.moveCamera(CameraUpdate.newLatLng(_point!));
                }
              },
              polylines: {
                if (_route.isNotEmpty)
                  Polyline(
                      polylineId: const PolylineId('sample'),
                      points: _route,
                      color: Colors.grey,
                      patterns: [PatternItem.dash(12), PatternItem.gap(8)]),
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
                      infoWindow:
                          InfoWindow(title: _stops[i]['name'] as String),
                      icon: BitmapDescriptor.defaultMarkerWithHue(
                          BitmapDescriptor.hueGreen)),
                if (_point != null)
                  Marker(
                      markerId: const MarkerId('bus'),
                      position: _point!,
                      infoWindow: InfoWindow(title: _plate))
              },
            );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final stale = _locationUpdatedAt != null &&
        DateTime.now().toUtc().difference(_locationUpdatedAt!.toUtc()) >
            const Duration(minutes: 2);
    final live = _point != null &&
        !stale &&
        !_locationError &&
        (!widget.driver || _sharing);
    final color = live ? const Color(0xFF087F5B) : const Color(0xFF9A6700);
    final title = _locationError
        ? 'Connection needs attention'
        : stale
            ? 'Bus location is stale'
            : _sharing
                ? 'Sharing your location'
                : live
                    ? 'Live bus location'
                    : widget.driver
                        ? 'Ready for your trip'
                        : 'Waiting for the bus';
    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_plate.isEmpty ? 'Live Bus Map' : _plate,
              maxLines: 1, overflow: TextOverflow.ellipsis),
          Text(widget.driver ? 'Your trip companion' : 'Your child’s bus',
              style: const TextStyle(fontSize: 12, color: Colors.white70)),
        ]),
        actions: [
          IconButton(
              tooltip: 'Shared devices',
              icon: const Icon(Icons.share_location),
              onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                      builder: (_) => const SharedDevicesScreen())))
        ],
      ),
      body: LayoutBuilder(
          builder: (context, constraints) => Column(children: [
                Expanded(
                    child: Stack(children: [
                  Positioned.fill(
                      child: Listener(
                    onPointerDown: (_) {
                      if (_followBus) setState(() => _followBus = false);
                    },
                    child: _mapView(),
                  )),
                  Positioned(
                      top: 16,
                      right: 16,
                      child: SafeArea(
                        top: false,
                        bottom: false,
                        child: Material(
                          elevation: 3,
                          borderRadius: BorderRadius.circular(16),
                          color: theme.colorScheme.surface,
                          child: TextButton.icon(
                            onPressed: _point == null ? null : _follow,
                            icon: Icon(_followBus
                                ? Icons.gps_fixed
                                : Icons.my_location),
                            label: Text(
                                _followBus ? 'Following bus' : 'Follow bus'),
                          ),
                        ),
                      )),
                ])),
                Material(
                  color: theme.colorScheme.surface,
                  elevation: 8,
                  borderRadius:
                      const BorderRadius.vertical(top: Radius.circular(24)),
                  child: SafeArea(
                      top: false,
                      child: ConstrainedBox(
                        constraints: BoxConstraints(
                            maxHeight: constraints.maxHeight * 0.5),
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                          padding: const EdgeInsets.all(12),
                                          decoration: BoxDecoration(
                                              color:
                                                  color.withValues(alpha: 0.1),
                                              borderRadius:
                                                  BorderRadius.circular(14)),
                                          child: Icon(
                                              _locationError
                                                  ? Icons.wifi_off_rounded
                                                  : Icons
                                                      .directions_bus_rounded,
                                              color: color)),
                                      const SizedBox(width: 12),
                                      Expanded(
                                          child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                            Text(title,
                                                style: theme
                                                    .textTheme.titleMedium
                                                    ?.copyWith(
                                                        fontWeight:
                                                            FontWeight.w700,
                                                        color: color)),
                                            const SizedBox(height: 2),
                                            Text(_ageLabel,
                                                style:
                                                    theme.textTheme.bodySmall),
                                          ])),
                                    ]),
                                if (_point == null ||
                                    _locationError ||
                                    (_sharing && _lastUpload == null))
                                  Padding(
                                      padding: const EdgeInsets.only(top: 10),
                                      child: Text(_status)),
                                if (!widget.driver && _child.isNotEmpty)
                                  Padding(
                                      padding: const EdgeInsets.only(top: 12),
                                      child: Text(
                                          '$_child · ${_childStatus.isEmpty ? "Checking boarding status…" : _childStatus}',
                                          style: theme.textTheme.bodyMedium)),
                                const SizedBox(height: 14),
                                if (widget.driver) ...[
                                  FilledButton.icon(
                                    style: _sharing
                                        ? FilledButton.styleFrom(
                                            backgroundColor:
                                                theme.colorScheme.error)
                                        : null,
                                    onPressed: _sharing
                                        ? _stop
                                        : _busy
                                            ? null
                                            : _busId == null
                                                ? _loadBus
                                                : _start,
                                    icon: _busy
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                                strokeWidth: 2))
                                        : Icon(_sharing
                                            ? Icons.stop_rounded
                                            : Icons.navigation_rounded),
                                    label: Text(_sharing
                                        ? 'Stop sharing'
                                        : _busy
                                            ? 'Starting…'
                                            : _busId == null
                                                ? 'Retry bus assignment'
                                                : 'Start sharing'),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                      _sharing
                                          ? 'Keep this screen open so parents can follow the bus.'
                                          : 'Share your phone’s location with parents assigned to this bus.',
                                      textAlign: TextAlign.center,
                                      style: theme.textTheme.bodySmall),
                                ] else
                                  OutlinedButton.icon(
                                      onPressed: _reading ? null : _loadBus,
                                      icon: const Icon(Icons.refresh_rounded),
                                      label: const Text('Refresh tracking')),
                                Theme(
                                  data: theme.copyWith(
                                      dividerColor: Colors.transparent),
                                  child: ExpansionTile(
                                    tilePadding: EdgeInsets.zero,
                                    childrenPadding:
                                        const EdgeInsets.only(bottom: 12),
                                    title: const Text('Trip details'),
                                    leading: const Icon(
                                        Icons.info_outline_rounded,
                                        size: 20),
                                    children: [
                                      if (_point != null)
                                        Align(
                                            alignment: Alignment.centerLeft,
                                            child: SelectableText(
                                                'Bus coordinates: ${_point!.latitude.toStringAsFixed(5)}, ${_point!.longitude.toStringAsFixed(5)}')),
                                      const SizedBox(height: 8),
                                      const Align(
                                          alignment: Alignment.centerLeft,
                                          child: Text(
                                              'Blue line: recorded journey · Grey line: sample route · Green pins: sample stops')),
                                      if (widget.driver)
                                        const Padding(
                                            padding: EdgeInsets.only(top: 8),
                                            child: Text(
                                                'Sharing stops when you leave this screen or put the app in the background.')),
                                    ],
                                  ),
                                ),
                              ]),
                        ),
                      )),
                ),
              ])),
    );
  }

  @override
  void dispose() {
    ++_session;
    WidgetsBinding.instance.removeObserver(this);
    _positions?.cancel();
    _poll?.cancel();
    _detailsPoll?.cancel();
    _statusClock?.cancel();
    _map?.dispose();
    super.dispose();
  }
}
