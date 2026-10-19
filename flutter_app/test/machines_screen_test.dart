import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/driver/machines_screen.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

void main() {
  testWidgets('Driver registers boarding machine and maps enrolled IDs', (tester) async {
    FlutterSecureStorage.setMockInitialValues({});
    final client = ApiClient(const FlutterSecureStorage());
    Map<String, dynamic>? saved;
    client.dio.interceptors.add(InterceptorsWrapper(onRequest: (request, handler) {
      if (request.method == 'PUT') {
        expect(request.path, '/driver/machines/ENTRY');
        saved = Map<String, dynamic>.from(request.data as Map);
        handler.resolve(Response(requestOptions: request, statusCode: 200, data: saved));
      } else {
        handler.resolve(Response(requestOptions: request, statusCode: 200, data: {
          'bus_id': 1, 'plate_no': 'BUS-REAL',
          'students': [{'id': 42, 'name': 'Actual student', 'grade': '5'}],
          'machines': saved == null ? [] : [{...saved!, 'role': 'ENTRY', 'last_seen_at': null}],
        }));
      }
    }));
    await tester.pumpWidget(ProviderScope(overrides: [apiClientProvider.overrideWithValue(client)],
      child: const MaterialApp(home: MachinesScreen())));
    await tester.pumpAndSettle();
    expect(find.text('Boarding machine'), findsOneWidget);
    expect(find.text('Exit machine'), findsOneWidget);
    await tester.tap(find.text('Register machine').first);
    await tester.pumpAndSettle();
    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'SERIAL-IN');
    await tester.enterText(fields.at(1), 'ZKTeco model');
    await tester.enterText(fields.at(3), '1001');
    await tester.ensureVisible(find.text('Save machine'));
    await tester.tap(find.text('Save machine'));
    await tester.pumpAndSettle();
    expect(saved!['students'], {'1001': 42});
    expect(saved!['serial'], 'SERIAL-IN');
    expect(find.text('ZKTeco model · SERIAL-IN'), findsOneWidget);
    expect(find.text('Not registered'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}
