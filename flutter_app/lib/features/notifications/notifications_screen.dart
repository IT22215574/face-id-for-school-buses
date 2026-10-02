import 'package:flutter/material.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = [
      'Aisha boarded the bus at 7:42 AM',
      'Noah arrived home at 3:15 PM',
      'Bus 24 is 2 minutes late',
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: ListView.separated(
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(),
        itemBuilder: (context, index) => ListTile(
          leading: const Icon(Icons.notifications_active, color: Colors.blue),
          title: Text(items[index]),
          subtitle: const Text('Just now'),
        ),
      ),
    );
  }
}
