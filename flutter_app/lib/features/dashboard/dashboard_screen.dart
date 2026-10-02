import 'package:flutter/material.dart';

import '../child_detail/child_detail_screen.dart';
import '../map/map_screen.dart';
import '../notifications/notifications_screen.dart';
import '../settings/settings_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final children = [
      _StudentCard(name: 'Aisha', status: 'ON_BUS', busNo: 'Bus 24', route: 'North Loop'),
      _StudentCard(name: 'Noah', status: 'OFF_BUS', busNo: 'Bus 11', route: 'West Loop'),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Parent Dashboard'),
        actions: [
          IconButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const NotificationsScreen())),
            icon: const Icon(Icons.notifications_none),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Your children', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          ...children.map((child) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: child,
              )),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.map), label: 'Map'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
        onDestinationSelected: (index) {
          if (index == 1) {
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MapScreen()));
          }
          if (index == 2) {
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
          }
        },
      ),
    );
  }
}

class _StudentCard extends StatelessWidget {
  const _StudentCard({required this.name, required this.status, required this.busNo, required this.route});

  final String name;
  final String status;
  final String busNo;
  final String route;

  @override
  Widget build(BuildContext context) {
    final isOnBus = status == 'ON_BUS';
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: isOnBus ? Colors.green : Colors.grey,
          child: const Icon(Icons.person, color: Colors.white),
        ),
        title: Text(name),
        subtitle: Text('$busNo · $route'),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: isOnBus ? Colors.green.shade100 : Colors.grey.shade200,
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(status, style: TextStyle(color: isOnBus ? Colors.green.shade800 : Colors.grey.shade800)),
        ),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => ChildDetailScreen(studentName: name)),
          );
        },
      ),
    );
  }
}
