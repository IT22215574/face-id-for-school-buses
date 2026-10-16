import 'package:flutter/material.dart';
import '../../core/bus_ui.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});
  @override
  Widget build(BuildContext context) => BusScaffold(
      title: 'Notifications',
      padding: const EdgeInsets.all(24),
      child: Column(children: [
        for (final item in const [
          ('Reminder!', 'The morning pickup is at 07:30 AM.', '07:00 AM'),
          ('Boarded the bus', 'Kavindu boarded bus WP NC-1234.', '07:30 AM'),
          ('Arrived at school', 'The morning journey is complete.', '08:15 AM'),
          ('Reminder!', 'The evening pickup is at 03:00 PM.', '02:30 PM'),
          (
            'Transport update',
            'Sample notifications for the UI preview.',
            '03:00 PM'
          ),
        ])
          Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: BusCard(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Row(children: [
                      const Icon(Icons.notifications_active_outlined,
                          color: busBlue, size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                          child: Text(item.$1,
                              style: const TextStyle(
                                  fontSize: 16, fontWeight: FontWeight.w600))),
                      Text(item.$3,
                          style: const TextStyle(color: busMuted, fontSize: 13))
                    ]),
                    const SizedBox(height: 12),
                    Text(item.$2, style: const TextStyle(color: busMuted)),
                  ]))),
      ]));
}
