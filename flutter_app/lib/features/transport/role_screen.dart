import 'package:flutter/material.dart';
import '../../core/bus_ui.dart';
import '../driver/driver_screen.dart';
import 'student_screens.dart';

class RoleScreen extends StatelessWidget {
  const RoleScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
      backgroundColor: busBlue,
      body: SafeArea(
          child: Center(
              child: SingleChildScrollView(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.directions_bus_rounded,
                            color: Colors.white, size: 96),
                        const SizedBox(height: 24),
                        const Text('School Bus',
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: 30,
                                fontWeight: FontWeight.bold)),
                        const SizedBox(height: 12),
                        const Text('Choose your side',
                            style:
                                TextStyle(color: Colors.white, fontSize: 18)),
                        const SizedBox(height: 40),
                        SizedBox(
                            width: 320,
                            child: FilledButton.icon(
                                style: FilledButton.styleFrom(
                                    backgroundColor: Colors.white,
                                    foregroundColor: busBlue),
                                onPressed: () => openScreen(
                                    context, const SelectChildScreen()),
                                icon: const Icon(Icons.family_restroom),
                                label: const Text('Parent'))),
                        const SizedBox(height: 16),
                        SizedBox(
                            width: 320,
                            child: FilledButton.icon(
                                style: FilledButton.styleFrom(
                                    backgroundColor: Colors.white,
                                    foregroundColor: busBlue),
                                onPressed: () =>
                                    openScreen(context, const DriverScreen(), name: 'transport-home'),
                                icon: const Icon(Icons.directions_bus),
                                label: const Text('Bus driver'))),
                        const SizedBox(height: 24),
                        const Text('UI preview · sample transport data',
                            style:
                                TextStyle(color: Colors.white70, fontSize: 12)),
                      ])))));
}
