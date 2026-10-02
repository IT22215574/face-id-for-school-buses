import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final CameraPosition _initialPosition = const CameraPosition(
    target: LatLng(6.9271, 79.8612),
    zoom: 13,
  );
  final Map<MarkerId, Marker> _markers = {};
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 10), (_) {
      setState(() {
        final id = const MarkerId('bus-location');
        final next = const LatLng(6.9271, 79.8612);
        _markers[id] = Marker(
          markerId: id,
          position: next,
          infoWindow: const InfoWindow(title: 'Bus 24'),
        );
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Live Bus Map')),
      body: GoogleMap(
        initialCameraPosition: _initialPosition,
        markers: _markers.values.toSet(),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
