import 'package:flutter/material.dart';
import 'live_map_screen.dart';

class MapScreen extends StatelessWidget {
  const MapScreen({super.key, this.driver = false});
  final bool driver;
  @override
  Widget build(BuildContext context) => LiveMapScreen(driver: driver);
}
