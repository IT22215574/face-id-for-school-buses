import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../../models/event.dart';
import '../../providers/auth_provider.dart';

final studentJourneyProvider =
    FutureProvider.autoDispose.family<List<BusEvent>, int>((ref, id) async {
  final timer = Timer(const Duration(seconds: 10), ref.invalidateSelf);
  ref.onDispose(timer.cancel);
  ref.watch(authStateProvider);
  final now = DateTime.now();
  final start = DateTime(now.year, now.month, now.day);
  final end = DateTime(now.year, now.month, now.day + 1);
  final response = await ref
      .read(apiClientProvider)
      .dio
      .get('/students/$id/events', queryParameters: {
    'from': start.toUtc().toIso8601String(),
    'to': end.toUtc().toIso8601String(),
  });
  return (response.data as List)
      .map((e) => BusEvent.fromJson(Map<String, dynamic>.from(e as Map)))
      .where((e) => !e.eventTime.isBefore(start) && e.eventTime.isBefore(end))
      .toList()
    ..sort((a, b) {
      final order = a.eventTime.compareTo(b.eventTime);
      return order != 0 ? order : a.id.compareTo(b.id);
    });
});

class StudentJourney extends ConsumerWidget {
  const StudentJourney({super.key, required this.studentId});
  final int? studentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (studentId == null) {
      return const BusCard(child: Text('No student linked.'));
    }
    final events = ref.watch(studentJourneyProvider(studentId!));
    return BusCard(
        child: events.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => Column(children: [
        const Text('Could not load today’s scans.'),
        TextButton(
            onPressed: () => ref.invalidate(studentJourneyProvider(studentId!)),
            child: const Text('Retry')),
      ]),
      data: (items) => items.isEmpty
          ? const Text(
              'No scans recorded today. Boarding and drop-off times will appear after the face ID machine sends them.')
          : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              for (final event in items)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                      event.eventType == 'BOARDED' ? Icons.login : Icons.logout,
                      color: busBlue),
                  title: Text(event.eventType == 'BOARDED'
                      ? 'Got on the bus'
                      : 'Dropped off'),
                  subtitle: Text(
                      TimeOfDay.fromDateTime(event.eventTime.toLocal())
                              .format(context) +
                          (event.isDelayed
                              ? '\nDelayed upload · original scan time shown'
                              : '') +
                          (event.gpsStatus == null
                              ? ''
                              : '\nGPS: ${event.gpsStatus}')),
                ),
              const Text('Recorded scans · updates every 10 seconds',
                  style: TextStyle(color: busMuted, fontSize: 12)),
            ]),
    ));
  }
}
