import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/features/admin/admin_screen.dart';

void main() {
  testWidgets('Registration requires driver details, both photos and a bus',
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
    expect(
        find.text('Enter Full name (at least 2 characters)'), findsOneWidget);
    expect(find.textContaining('Unable to save'), findsNothing);
  });
}
