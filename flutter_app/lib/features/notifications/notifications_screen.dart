import 'package:flutter/material.dart';
import '../../core/bus_ui.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});
  @override
  Widget build(BuildContext context) => BusScaffold(
      title: 'Notification',
      padding: const EdgeInsets.symmetric(vertical: 36),
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
          Container(
              margin: const EdgeInsets.only(bottom: 2),
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 22),
              constraints: const BoxConstraints(minHeight: 123),
              color: const Color(0xFFDFE2E7),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Expanded(
                          child: Text(item.$1,
                              style: const TextStyle(fontSize: 20))),
                      Text(item.$3,
                          style: const TextStyle(color: busMuted, fontSize: 13))
                    ]),
                    const SizedBox(height: 12),
                    Text(item.$2, style: const TextStyle(color: busMuted)),
                  ])),
      ]));
}
