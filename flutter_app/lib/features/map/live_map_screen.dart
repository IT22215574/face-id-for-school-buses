import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class LiveMapScreen extends StatefulWidget {
  const LiveMapScreen({super.key});

  @override
  State<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends State<LiveMapScreen> {
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
        const id = MarkerId('bus-location');
        const next = LatLng(6.9271, 79.8612);
        _markers[id] = const Marker(
          markerId: id,
          position: next,
          infoWindow: InfoWindow(title: 'Bus 24'),
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
