import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

final faceDevicesProvider =
    FutureProvider.autoDispose<List<dynamic>>((ref) async {
  ref.watch(authStateProvider);
  final timer = Timer(const Duration(seconds: 15), ref.invalidateSelf);
  ref.onDispose(timer.cancel);
  return (await ref.read(apiClientProvider).dio.get('/admin/face-devices')).data
      as List;
});
final faceEventsProvider =
    FutureProvider.autoDispose<List<dynamic>>((ref) async {
  ref.watch(authStateProvider);
  final timer = Timer(const Duration(seconds: 10), ref.invalidateSelf);
  ref.onDispose(timer.cancel);
  return (await ref.read(apiClientProvider).dio.get('/admin/face-events')).data
      as List;
});

class FaceDevicesScreen extends ConsumerStatefulWidget {
  const FaceDevicesScreen({super.key});
  @override
  ConsumerState<FaceDevicesScreen> createState() => _FaceDevicesScreenState();
}

class _FaceDevicesScreenState extends ConsumerState<FaceDevicesScreen> {
  String? error;
  bool busy = false;
  Dio get api => ref.read(apiClientProvider).dio;
  String time(dynamic value) => value == null
      ? 'Unavailable'
      : (DateTime.tryParse(value.toString())?.toLocal().toString() ??
          'Invalid time');

  Future<void> act(Future<void> Function() action) async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await action();
      ref.invalidate(faceDevicesProvider);
      ref.invalidate(faceEventsProvider);
    } catch (e) {
      if (mounted) {
        final detail = e is DioException && e.response?.data is Map
            ? e.response?.data['detail']
            : null;
        setState(() => error = detail is String
            ? detail
            : 'Unable to save. Check the fields and retry.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<Map<String, String>?> form(String title, Map<String, String> labels,
      {String? guidance}) async {
    final controllers = {
      for (final key in labels.keys) key: TextEditingController()
    };
    final key = GlobalKey<FormState>();
    final result = await showDialog<Map<String, String>>(
        context: context,
        builder: (context) => AlertDialog(
              title: Text(title),
              content: SingleChildScrollView(
                  child: Form(
                      key: key,
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        if (guidance != null) Text(guidance),
                        for (final entry in labels.entries)
                          TextFormField(
                              controller: controllers[entry.key],
                              decoration:
                                  InputDecoration(labelText: entry.value),
                              validator: (v) =>
                                  (v ?? '').trim().isEmpty ? 'Required' : null),
                      ]))),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () {
                      if (key.currentState!.validate()) {
                        Navigator.pop(context, {
                          for (final entry in controllers.entries)
                            entry.key: entry.value.text.trim()
                        });
                      }
                    },
                    child: const Text('Save'))
              ],
            ));
    // The route exit animation may still be using the controllers.
    await Future<void>.delayed(const Duration(milliseconds: 300));
    for (final controller in controllers.values) {
      controller.dispose();
    }
    return result;
  }

  Future<void> register() async {
    final values = await form(
        'Register face recognition device',
        {
          'serial': 'Serial number',
          'device_name': 'Device name',
          'model': 'Model',
          'firmware_version': 'Firmware version',
          'bus_id': 'Assigned bus ID',
          'timezone': 'Timezone (e.g. Asia/Colombo)',
          'role': 'Door slot: ENTRY or EXIT',
        },
        guidance:
            'Confirm the bus ID in bus administration. Hardware compatibility must be tested separately.');
    if (values == null) return;
    await act(() async {
      await api.post('/admin/face-devices',
          data: {...values, 'bus_id': int.parse(values['bus_id']!)});
    });
  }

  Future<void> mapping(Map device) async {
    final values = await form(
        'Confirm manual enrollment',
        {
          'terminal_user_id': 'Terminal user ID',
          'student_id': 'School student ID',
          'effective_from': 'Enrollment start (ISO time with timezone)',
          'consent_reference': 'Consent register reference',
        },
        guidance:
            'Enroll the face on the terminal first. Saving confirms enrollment and consent. Use the actual enrollment start time for buffered scans.');
    if (values == null) return;
    await act(() async {
      await api.post('/admin/face-devices/${device['id']}/enrollments', data: {
        ...values,
        'student_id': int.parse(values['student_id']!),
        'manual_enrollment_confirmed': true,
      });
    });
  }

  Future<void> viewMappings(Map device) async {
    await act(() async {
      final rows =
          (await api.get('/admin/face-devices/${device['id']}/enrollments'))
              .data as List;
      if (!mounted) {
        return;
      }
      final selected = await showDialog<int>(
          context: context,
          builder: (context) => AlertDialog(
                title: Text('Enrollment · bus ${device['bus_id']}'),
                content: SizedBox(
                    width: 500,
                    child: ListView(shrinkWrap: true, children: [
                      if (rows.isEmpty) const Text('No confirmed mappings'),
                      for (final row in rows)
                        ListTile(
                            title: Text(
                                '${row['student_name']} · ${row['student_id']}'),
                            subtitle: Text(
                                'Terminal ID ${row['terminal_user_id']} · ${row['enrollment_status']}\nFrom ${time(row['effective_from'])}'),
                            trailing: row['effective_until'] == null
                                ? TextButton(
                                    onPressed: () => Navigator.pop(
                                        context, row['id'] as int),
                                    child: const Text('End mapping'))
                                : null),
                    ])),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Close'))
                ],
              ));
      if (selected != null) {
        await api.delete(
            '/admin/face-devices/${device['id']}/enrollments/$selected');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
              content: Text(
                  'Mapping ended. Delete the face enrollment on the terminal and record completion in the consent register.')));
        }
      }
    });
  }

  Future<void> verifyClock(Map device) async {
    final values = await form(
        'Record terminal clock check',
        {
          'observed_error_seconds': 'Observed absolute clock error (seconds)',
          'valid_until':
              'Verification expiry (ISO time with timezone, within 24h)',
          'evidence': 'Physical check evidence / register reference',
        },
        guidance:
            'Compare the terminal clock with UTC now. Only confirm after physical verification. Repeat after clock changes or power loss.');
    if (values == null) {
      return;
    }
    await act(() async {
      await api.post('/admin/face-devices/${device['id']}/clock-check', data: {
        ...values,
        'observed_error_seconds':
            double.parse(values['observed_error_seconds']!),
      });
    });
  }

  Future<void> reconcile(Map job) async {
    final values = await form(
        'Reconcile notification delivery',
        {
          'resolution': 'DELIVERED or RETRY',
          'evidence': 'Provider evidence / operator register reference',
        },
        guidance:
            'Stop the notification worker first. Check the provider audit before authorizing a retry; an ambiguous send may already have arrived.');
    if (values == null) {
      return;
    }
    await act(() async {
      await api.post('/admin/face-notifications/${job['id']}/reconcile',
          data: values);
    });
  }

  Future<void> classify(Map event) async {
    final values = await form('Supervised scan classification',
        {'event_type': 'BOARDED or ALIGHTED', 'reason': 'Evidence / reason'},
        guidance:
            'Confirm what happened at the original scan time. This creates attendance and queues parent notifications.');
    if (values == null) return;
    await act(() async {
      await api.post('/admin/face-events/${event['id']}/classify',
          data: values);
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Face Recognition Devices'), actions: [
          IconButton(
              onPressed: busy
                  ? null
                  : () {
                      ref.invalidate(faceDevicesProvider);
                      ref.invalidate(faceEventsProvider);
                    },
              icon: const Icon(Icons.refresh)),
        ]),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          const Text(
              'Compatibility unverified. Recognition and biometric enrollment remain on the terminal.'),
          if (error != null)
            Text(error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (busy) const LinearProgressIndicator(),
          FilledButton.icon(
              onPressed: busy ? null : register,
              icon: const Icon(Icons.add),
              label: const Text('Register device')),
          ref.watch(faceDevicesProvider).when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) =>
                  const Text('Unable to load devices. Refresh to retry.'),
              data: (devices) => Column(children: [
                    if (devices.isEmpty) const Text('No devices registered'),
                    for (final device in devices)
                      Card(
                          child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                        '${device['device_name'] ?? device['serial']} · Bus ${device['bus_id']}',
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleMedium),
                                    Text(
                                        '${device['model']} · ${device['serial']}\nFirmware: ${device['firmware_version'] ?? 'Unknown'}\n${device['connection_status']} · ${device['configuration_status']}\nLast attendance upload: ${time(device['last_seen_at'])}\nClock verified until: ${time(device['clock_verified_until'])}'),
                                    Wrap(spacing: 8, children: [
                                      if (device['adapter_managed'] != true)
                                        TextButton(
                                            onPressed: busy
                                                ? null
                                                : () => act(() async {
                                                      await api.post(
                                                          '/admin/face-devices/${device['id']}/adopt');
                                                    }),
                                            child: const Text(
                                                'Use receiver adapter')),
                                      TextButton(
                                          onPressed: busy
                                              ? null
                                              : () => mapping(device as Map),
                                          child:
                                              const Text('Confirm enrollment')),
                                      TextButton(
                                          onPressed: busy
                                              ? null
                                              : () =>
                                                  viewMappings(device as Map),
                                          child:
                                              const Text('Student mappings')),
                                      TextButton(
                                          onPressed: busy
                                              ? null
                                              : () =>
                                                  verifyClock(device as Map),
                                          child: const Text('Verify clock')),
                                      for (final direction in [
                                        'BOARDED',
                                        'ALIGHTED'
                                      ])
                                        TextButton(
                                            onPressed: busy ||
                                                    device['enabled'] != true
                                                ? null
                                                : () => act(() async {
                                                      await api.post(
                                                          '/face-devices/${device['id']}/direction',
                                                          data: {
                                                            'event_type':
                                                                direction
                                                          });
                                                    }),
                                            child: Text('Set $direction mode')),
                                      TextButton(
                                          onPressed: busy
                                              ? null
                                              : () => act(() async {
                                                    await api.patch(
                                                        '/admin/face-devices/${device['id']}',
                                                        data: {
                                                          'device_name': device[
                                                                  'device_name'] ??
                                                              device['serial'],
                                                          'firmware_version':
                                                              device[
                                                                  'firmware_version'],
                                                          'enabled': device[
                                                                  'enabled'] !=
                                                              true,
                                                        });
                                                  }),
                                          child: Text(device['enabled'] == true
                                              ? 'Disable device'
                                              : 'Enable device')),
                                    ]),
                                  ]))),
                  ])),
          const Divider(),
          Text('Recent attendance & processing errors',
              style: Theme.of(context).textTheme.titleLarge),
          ref.watch(faceEventsProvider).when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) =>
                  const Text('Unable to load attendance. Refresh to retry.'),
              data: (events) => Column(children: [
                    if (events.isEmpty)
                      const Text('No receiver attendance records'),
                    for (final event in events)
                      Card(
                          child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                        '${event['student_name'] ?? 'Terminal ID ${event['terminal_user_id']}'} · Bus ${event['bus_id']}'),
                                    Text(
                                        '${event['event_type'] ?? 'Unclassified'} · ${event['processing_status']}\nScan: ${time(event['device_event_time'])}\nReceived: ${time(event['received_at'])}\nGPS: ${event['gps_status'] ?? 'Pending'} · ${event['is_delayed'] == true ? 'Delayed upload' : ''}\nSource: ${event['source']} · Duplicates: ${event['duplicate_count']}'),
                                    if (event['processing_error'] != null)
                                      Text(
                                          event['processing_error'].toString()),
                                    if ((event['notifications'] as List)
                                        .isNotEmpty)
                                      Text(
                                          'Notifications: ${(event['notifications'] as List).map((j) => j['status']).join(', ')}'),
                                    for (final job
                                        in event['notifications'] as List)
                                      if (['SENDING', 'UNCERTAIN', 'FAILED']
                                          .contains(job['status']))
                                        TextButton(
                                            onPressed: busy
                                                ? null
                                                : () => reconcile(job as Map),
                                            child: Text(
                                                'Review notification ${job['id']} · ${job['status']}')),
                                    if (event['processing_status'] == 'PENDING')
                                      Wrap(children: [
                                        TextButton(
                                            onPressed: busy
                                                ? null
                                                : () => classify(event as Map),
                                            child: const Text('Classify scan')),
                                        TextButton(
                                            onPressed: busy
                                                ? null
                                                : () => act(() async {
                                                      await api.post(
                                                          '/admin/face-events/${event['id']}/reprocess');
                                                    }),
                                            child: const Text('Reprocess')),
                                      ]),
                                  ]))),
                  ])),
        ]),
      );
}
