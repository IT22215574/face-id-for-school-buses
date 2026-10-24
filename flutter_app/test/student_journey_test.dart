import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/dashboard/student_journey.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

void main() {
  testWidgets('Journey follows selected student and refreshes scans',
      (tester) async {
    FlutterSecureStorage.setMockInitialValues({});
    final client = ApiClient(const FlutterSecureStorage());
    var reads = 0;
    client.dio.interceptors
        .add(InterceptorsWrapper(onRequest: (request, handler) {
      reads++;
      final isFirst = request.path == '/students/42/events';
      final when = DateTime.now().toUtc();
      handler.resolve(Response(
          requestOptions: request,
          statusCode: 200,
          data: isFirst
              ? [
                  {
                    'id': 1,
                    'student_id': 42,
                    'bus_id': 1,
                    'event_type': 'BOARDED',
                    'event_time': when.toIso8601String(),
                    'lat': null,
                    'lng': null,
                    'is_delayed': true,
                    'gps_status': 'UNAVAILABLE',
                    'source': 'ZK:test'
                  },
                  if (reads > 1)
                    {
                      'id': 2,
                      'student_id': 42,
                      'bus_id': 1,
                      'event_type': 'ALIGHTED',
                      'event_time': when.toIso8601String(),
                      'lat': null,
                      'lng': null,
                      'source': 'ZK:test'
                    },
                ]
              : []));
    }));
    Widget screen(int id) => ProviderScope(
        overrides: [apiClientProvider.overrideWithValue(client)],
        child:
            MaterialApp(home: Scaffold(body: StudentJourney(studentId: id))));
    await tester.pumpWidget(screen(42));
    await tester.pumpAndSettle();
    expect(find.text('Got on the bus'), findsOneWidget);
    expect(find.text('Dropped off'), findsNothing);
    expect(find.textContaining('Delayed upload'), findsOneWidget);
    expect(find.textContaining('GPS: UNAVAILABLE'), findsOneWidget);
    expect(find.textContaining('Sample'), findsNothing);
    await tester.pump(const Duration(seconds: 10));
    await tester.pumpAndSettle();
    expect(find.text('Dropped off'), findsOneWidget);
    await tester.pumpWidget(screen(43));
    await tester.pumpAndSettle();
    expect(find.text('Got on the bus'), findsNothing);
    expect(find.textContaining('No scans recorded today'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}
