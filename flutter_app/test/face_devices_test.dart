import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/admin/face_devices_screen.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

void main() {
  testWidgets(
      'Admin monitors uncertain attendance and classifies with evidence',
      (tester) async {
    FlutterSecureStorage.setMockInitialValues({});
    final client = ApiClient(const FlutterSecureStorage());
    Map<String, dynamic>? classification;
    client.dio.interceptors
        .add(InterceptorsWrapper(onRequest: (request, handler) {
      expect(request.path, '/admin/face-events/7/classify');
      classification = Map<String, dynamic>.from(request.data as Map);
      handler.resolve(Response(
          requestOptions: request,
          statusCode: 200,
          data: {'status': 'PROCESSED'}));
    }));
    await tester.pumpWidget(ProviderScope(overrides: [
      apiClientProvider.overrideWithValue(client),
      faceDevicesProvider.overrideWith((ref) async => []),
      faceEventsProvider.overrideWith((ref) async => [
            {
              'id': 7,
              'terminal_user_id': 'SYNTHETIC-1001',
              'bus_id': 1,
              'student_name': null,
              'processing_status': 'PENDING',
              'device_event_time': '2026-10-20T02:00:00Z',
              'received_at': '2026-10-20T05:00:00Z',
              'event_type': null,
              'gps_status': null,
              'is_delayed': null,
              'source': 'RECEIVER_JSONL',
              'duplicate_count': 2,
              'processing_error': 'Unclassified direction',
              'notifications': <dynamic>[]
            },
          ]),
    ], child: const MaterialApp(home: FaceDevicesScreen())));
    await tester.pumpAndSettle();
    expect(find.text('Face Recognition Devices'), findsOneWidget);
    expect(find.text('Unclassified direction'), findsOneWidget);
    expect(find.textContaining('Duplicates: 2'), findsOneWidget);
    await tester.ensureVisible(find.text('Classify scan'));
    await tester.tap(find.text('Classify scan'));
    await tester.pumpAndSettle();
    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'ALIGHTED');
    await tester.enterText(fields.at(1), 'Synthetic supervised evidence');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(classification,
        {'event_type': 'ALIGHTED', 'reason': 'Synthetic supervised evidence'});
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Admin sees recoverable device and attendance loading errors',
      (tester) async {
    await tester.pumpWidget(ProviderScope(overrides: [
      faceDevicesProvider.overrideWith(
          (ref) async => throw Exception('synthetic private failure')),
      faceEventsProvider.overrideWith(
          (ref) async => throw Exception('synthetic private failure')),
    ], child: const MaterialApp(home: FaceDevicesScreen())));
    await tester.pumpAndSettle();
    expect(
        find.text('Unable to load devices. Refresh to retry.'), findsOneWidget);
    expect(find.text('Unable to load attendance. Refresh to retry.'),
        findsOneWidget);
    expect(find.textContaining('private failure'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
}
