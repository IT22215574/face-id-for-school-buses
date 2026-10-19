import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'tracking_service.dart';

class SharedDevicesScreen extends ConsumerStatefulWidget {
  const SharedDevicesScreen({super.key});
  @override
  ConsumerState<SharedDevicesScreen> createState() =>
      _SharedDevicesScreenState();
}

class _SharedDevicesScreenState extends ConsumerState<SharedDevicesScreen>
    with SingleTickerProviderStateMixin {
  final _viewer = TextEditingController();
  GoogleMapController? _map;
  bool _mapsReady = false, _background = false;
  String? _selected;
  Timer? _clock;
  late final AnimationController _motion;
  final _from = <String, LatLng>{};
  final _to = <String, LatLng>{};

  LatLng _displayPoint(String id, TrackedPoint point) {
    final end = _to[id] ?? LatLng(point.lat, point.lng);
    final start = _from[id] ?? end;
    final progress = Curves.easeOut.transform(_motion.value);
    // Interpolate over the shortest longitude arc across the date line.
    final delta = (end.longitude - start.longitude + 540) % 360 - 180;
    return LatLng(start.latitude + (end.latitude - start.latitude) * progress,
        (start.longitude + delta * progress + 540) % 360 - 180);
  }

  void _updatePoints(TrackingService service) {
    final changed = service.points.entries.any((entry) =>
        _to[entry.key] != LatLng(entry.value.lat, entry.value.lng));
    if (changed) {
      // Freeze every marker at its displayed position before restarting the
      // shared animation, so another device's update cannot replay old motion.
      for (final entry in service.points.entries) {
        _from[entry.key] = _displayPoint(entry.key, entry.value);
        _to[entry.key] = LatLng(entry.value.lat, entry.value.lng);
      }
    }
    _to.removeWhere((id, _) => !service.points.containsKey(id));
    _from.removeWhere((id, _) => !service.points.containsKey(id));
    if (changed) {
      _motion.forward(from: 0);
      final point = service.points[_selected];
      if (point != null) {
        _map?.animateCamera(
            CameraUpdate.newLatLng(LatLng(point.lat, point.lng)));
      }
    }
  }

  @override
  void initState() {
    super.initState();
    _motion = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 650))
      ..value = 1
      ..addListener(() {
        if (mounted) setState(() {});
      });
    _checkMaps();
    _clock = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() {});
    });
  }

  Future<void> _checkMaps() async {
    try {
      final configured =
          await const MethodChannel('school_bus/maps_configuration')
              .invokeMethod<bool>('isConfigured');
      if (mounted) setState(() => _mapsReady = configured == true);
    } on PlatformException {
      /* Show setup guidance below. */
    } on MissingPluginException {/* Native mobile maps required. */}
  }

  Future<void> _run(Future<void> Function() action) async {
    try {
      await action();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final tracking = ref.watch(trackingProvider);
    ref.listen(trackingProvider, (_, next) {
      _updatePoints(next);
    });
    return Scaffold(
      appBar: AppBar(title: const Text('Shared devices')),
      body: SafeArea(
          child: Column(children: [
        Expanded(
            child: !_mapsReady
                ? const Center(
                    child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                            'Google Maps is not configured. Add a restricted Maps key for this platform. Location sharing controls remain available.')))
                : GoogleMap(
                    initialCameraPosition: const CameraPosition(
                        target: LatLng(7.4863, 80.3647), zoom: 14),
                    onMapCreated: (controller) => _map = controller,
                    zoomControlsEnabled: true,
                    compassEnabled: true,
                    markers: tracking.points.entries.map((entry) {
                      final stale =
                          DateTime.now().difference(entry.value.updatedAt) >
                              const Duration(minutes: 2);
                      return Marker(
                          markerId: MarkerId(entry.key),
                          position: _displayPoint(entry.key, entry.value),
                          alpha: stale ? 0.5 : 1,
                          icon: BitmapDescriptor.defaultMarkerWithHue(
                              entry.key == tracking.uid
                                  ? BitmapDescriptor.hueAzure
                                  : BitmapDescriptor.hueRed),
                          infoWindow: InfoWindow(
                              title:
                                  entry.key == tracking.uid ? 'You' : entry.key,
                              snippet:
                                  '${stale ? "Stale · " : ""}${entry.value.updatedAt.toLocal()}'),
                          onTap: () => setState(() => _selected = entry.key));
                    }).toSet(),
                  )),
        ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 330),
            child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(children: [
                  Text(tracking.status, textAlign: TextAlign.center),
                  if (tracking.uid == null)
                    FilledButton(
                        onPressed:
                            tracking.busy ? null : () => tracking.connect(),
                        child: Text(tracking.busy
                            ? 'Connecting…'
                            : 'Connect location sharing')),
                  if (tracking.uid != null) ...[
                    SelectableText('Your sharing ID: ${tracking.uid}'),
                    SwitchListTile(
                        title: const Text('Continue sharing in background'),
                        subtitle: const Text(
                            'Uses battery. Tracking may stop if the OS terminates the app.'),
                        value: _background,
                        onChanged: tracking.sharing
                            ? null
                            : (value) => setState(() => _background = value)),
                    Wrap(spacing: 8, children: [
                      FilledButton(
                          onPressed: tracking.busy
                              ? null
                              : tracking.sharing
                                  ? tracking.stop
                                  : () =>
                                      tracking.start(inBackground: _background),
                          child: Text(tracking.sharing
                              ? 'Stop sharing'
                              : 'Start sharing')),
                      TextButton(
                          onPressed: () => _run(tracking.deleteLocation),
                          child: const Text('Delete my last location')),
                      TextButton(
                          onPressed: () => Geolocator.openAppSettings(),
                          child: const Text('App settings')),
                      TextButton(
                          onPressed: () => Geolocator.openLocationSettings(),
                          child: const Text('GPS settings')),
                    ]),
                    DropdownButton<String>(
                        value: tracking.points.containsKey(_selected)
                            ? _selected
                            : null,
                        hint: const Text('Choose a device to follow'),
                        isExpanded: true,
                        items: tracking.points.keys
                            .map((id) =>
                                DropdownMenuItem(value: id, child: Text(id)))
                            .toList(),
                        onChanged: (id) {
                          setState(() => _selected = id);
                          final point = tracking.points[id];
                          if (point != null) {
                            _map?.animateCamera(CameraUpdate.newLatLng(
                                LatLng(point.lat, point.lng)));
                          }
                        }),
                    if (_selected != null)
                      TextButton(
                          onPressed: () => setState(() => _selected = null),
                          child: const Text('Stop following')),
                    TextField(
                        controller: _viewer,
                        decoration: const InputDecoration(
                            labelText: 'Recipient sharing ID',
                            hintText: 'account_123')),
                    TextButton(
                        onPressed: () => _run(
                            () => tracking.grant(_viewer.text.trim(), true)),
                        child: const Text(
                            'Allow this account to see my location')),
                    for (final viewer in tracking.viewers)
                      ListTile(
                          title: Text(viewer),
                          trailing: TextButton(
                              onPressed: () =>
                                  _run(() => tracking.grant(viewer, false)),
                              child: const Text('Revoke'))),
                  ],
                ]))),
      ])),
    );
  }

  @override
  void dispose() {
    _motion.dispose();
    _clock?.cancel();
    _viewer.dispose();
    _map?.dispose();
    super.dispose();
  }
}
