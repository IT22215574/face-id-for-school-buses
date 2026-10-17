import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/driver/add_student_screen.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

class StudentAdapter implements HttpClientAdapter {
  Map<String, dynamic>? saved;
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream,
      Future<void>? cancelFuture) async {
    expect(options.path, '/driver/students');
    expect(options.method, 'POST');
    saved = Map<String, dynamic>.from(options.data as Map);
    return ResponseBody.fromString(jsonEncode({'id': 1}), 201, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType]
    });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  testWidgets('Driver validates and adds a child to their vehicle',
      (tester) async {
    FlutterSecureStorage.setMockInitialValues({});
    final client = ApiClient(const FlutterSecureStorage());
    final adapter = StudentAdapter();
    client.dio.httpClientAdapter = adapter;
    await tester.pumpWidget(ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(client),
          driverVehicleProvider.overrideWith((ref) async =>
              {'plate_no': 'BUS-1', 'route_name': 'School route'}),
          transportLoadProvider.overrideWith((ref) async {}),
        ],
        child: MaterialApp(
            home: Builder(
                builder: (context) => Scaffold(
                        body: TextButton(
                      onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                              builder: (_) => const AddStudentScreen())),
                      child: const Text('Open form'),
                    ))))));
    await tester.tap(find.text('Open form'));
    await tester.pumpAndSettle();
    expect(find.text('BUS-1'), findsOneWidget);
    await tester.ensureVisible(find.text('Add to my vehicle'));
    await tester.tap(find.text('Add to my vehicle'));
    await tester.pumpAndSettle();
    expect(adapter.saved, isNull);
    await tester.enterText(find.byType(TextFormField).at(0), 'New Child');
    await tester.enterText(find.byType(TextFormField).at(1), 'Grade 3');
    await tester.ensureVisible(find.byType(DropdownButtonFormField<String>));
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Maliyadeva College').last);
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byType(TextFormField).at(2), 'parent@example.com');
    await tester.enterText(find.byType(TextFormField).at(3), 'abc071123456789');
    expect(
        tester
            .widget<TextFormField>(find.byType(TextFormField).at(3))
            .controller!
            .text,
        '0711234567');
    await tester.enterText(find.byType(TextFormField).at(4), '077');
    await tester.ensureVisible(find.text('Add to my vehicle'));
    await tester.tap(find.text('Add to my vehicle'));
    await tester.pumpAndSettle();
    expect(adapter.saved, isNull);
    expect(find.text('Enter exactly 10 digits'), findsOneWidget);
    await tester.enterText(find.byType(TextFormField).at(4), '0771234567');
    await tester.ensureVisible(find.text('Add to my vehicle'));
    await tester.tap(find.text('Add to my vehicle'));
    await tester.pumpAndSettle();
    expect(adapter.saved, {
      'name': 'New Child',
      'grade': 'Grade 3',
      'school_id': 'KUR-MALIYADEVA',
      'parent_email': 'parent@example.com',
      'father_phone': '0711234567',
      'mother_phone': '0771234567'
    });
    expect(find.text('Student added to your vehicle'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
