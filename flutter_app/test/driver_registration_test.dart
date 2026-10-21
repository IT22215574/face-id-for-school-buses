import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/features/admin/admin_screen.dart';

void main() {
  testWidgets(
      'Registration requires driver details, ID and licence photos and a bus',
      (tester) async {
    await tester.pumpWidget(const ProviderScope(
        child: MaterialApp(
            home: DriverRegistrationScreen(buses: [
      {'id': 1, 'plate_no': 'BUS-1', 'route_name': 'School route'}
    ]))));
    final save = find.text('Create driver & assign bus');
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pump();
    final state = tester.state<FormState>(find.byType(Form));
    expect(state.validate(), isFalse);
    expect(find.text('Select a bus and route'), findsOneWidget);
    expect(find.text('Upload ID front photo'), findsOneWidget);
    expect(find.text('Upload ID back photo'), findsOneWidget);
    expect(find.text('Upload Driving licence front photo'), findsOneWidget);
    expect(find.text('Driving licence number'), findsNothing);
    expect(
        find.text('Enter Full name (at least 2 characters)'), findsOneWidget);
    expect(find.textContaining('Unable to save'), findsNothing);
  });
  testWidgets('Editing loads saved driver details and keeps password optional',
      (tester) async {
    const photo = 'data:image/png;base64,iVBORw0KGgo=';
    await tester.pumpWidget(const ProviderScope(
        child: MaterialApp(
      home: DriverRegistrationScreen(
        buses: [
          {'id': 1, 'plate_no': 'BUS-1', 'route_name': 'School route'}
        ],
        existing: {
          'id': 3,
          'bus_id': 1,
          'name': 'Saved Driver',
          'email': 'saved@example.com',
          'phone': '0771234567',
          'nic': '123456789V',
          'address': 'School Road',
          'id_front': photo,
          'id_back': photo,
          'license_front': photo,
        },
      ),
    )));
    expect(find.text('Edit bus driver'), findsOneWidget);
    expect(find.text('Saved Driver'), findsOneWidget);
    final state = tester.state<FormState>(find.byType(Form));
    expect(state.validate(), isTrue);
    await tester.pump();
    expect(find.text('Upload ID front photo'), findsNothing);
    await tester.ensureVisible(find.text('Save driver changes'));
    expect(find.text('Save driver changes'), findsOneWidget);
  });
}
