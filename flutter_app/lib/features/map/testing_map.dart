import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Key-free map used when the native Google Maps SDK is not configured.
class TestingMap extends StatefulWidget {
  const TestingMap(
      {super.key,
      required this.point,
      required this.route,
      required this.history,
      required this.stopNames,
      required this.plate,
      this.followBus = true,
      this.showRecenter = true,
      this.recenterSignal = 0});

  final LatLng? point;
  final List<LatLng> route;
  final List<LatLng> history;
  final List<String> stopNames;
  final String plate;
  final bool followBus, showRecenter;
  final int recenterSignal;

  @override
  State<TestingMap> createState() => _TestingMapState();
}

class _TestingMapState extends State<TestingMap> {
  final _controller = MapController();
  bool _ready = false;

  @override
  void didUpdateWidget(covariant TestingMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_ready &&
        widget.point != null &&
        ((widget.followBus && widget.point != oldWidget.point) ||
            widget.recenterSignal != oldWidget.recenterSignal)) {
      _controller.move(widget.point!, _controller.camera.zoom);
    }
  }

  @override
  Widget build(BuildContext context) => Stack(children: [
        FlutterMap(
          mapController: _controller,
          options: MapOptions(
            initialCenter: widget.point ??
                (widget.route.isNotEmpty
                    ? widget.route.first
                    : const LatLng(7.4863, 80.3647)),
            initialZoom: 14,
            maxZoom: 19,
            onMapReady: () => _ready = true,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.example.school_bus_parent_app',
            ),
            PolylineLayer(polylines: [
              if (widget.route.isNotEmpty)
                Polyline(
                    points: widget.route, color: Colors.grey, strokeWidth: 3),
              if (widget.history.isNotEmpty)
                Polyline(
                    points: widget.history, color: Colors.blue, strokeWidth: 5),
            ]),
            MarkerLayer(markers: [
              for (var i = 0; i < widget.route.length; i++)
                Marker(
                    point: widget.route[i],
                    width: 40,
                    height: 40,
                    child: Tooltip(
                        message: widget.stopNames[i],
                        child: const Icon(Icons.location_on,
                            color: Colors.green, size: 36))),
              if (widget.point != null)
                Marker(
                    point: widget.point!,
                    width: 48,
                    height: 48,
                    child: Tooltip(
                        message: 'Bus ${widget.plate}',
                        child: Container(
                            decoration: const BoxDecoration(
                                color: Colors.white, shape: BoxShape.circle),
                            child: const Icon(Icons.directions_bus,
                                color: Colors.blue, size: 34)))),
            ]),
            SafeArea(
                child: Align(
              alignment: Alignment.bottomRight,
              child: Material(
                color: Theme.of(context).colorScheme.surface,
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text('© ', style: Theme.of(context).textTheme.bodySmall),
                    Flexible(
                        child: Text('OpenStreetMap contributors',
                            style: Theme.of(context).textTheme.bodySmall)),
                  ]),
                ),
              ),
            )),
          ],
        ),
        if (widget.showRecenter)
          Positioned(
              top: 12,
              right: 12,
              child: FloatingActionButton.small(
                heroTag: 'recenter-testing-map',
                tooltip: 'Center on bus',
                onPressed: widget.point == null
                    ? null
                    : () => _controller.move(widget.point!, 15),
                child: const Icon(Icons.my_location),
              )),
      ]);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
