import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/app.dart';
import 'package:school_bus_parent_app/features/dashboard/dashboard_screen.dart';
import 'package:school_bus_parent_app/features/driver/driver_screen.dart';
import 'package:school_bus_parent_app/features/map/map_screen.dart';
import 'package:school_bus_parent_app/features/transport/student_screens.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';

void main() {
  Future<void> start(WidgetTester tester) async {
    tester.view.physicalSize = const Size(402, 874);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const ProviderScope(child: SchoolBusParentApp()));
    await tester.pumpAndSettle();
  }

  testWidgets('Parent selects and switches children, opens map and profiles', (tester) async {
    await start(tester);
    await tester.tap(find.text('Parent'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Kavindu Perera'));
    await tester.pumpAndSettle();
    expect(find.byType(DashboardScreen), findsOneWidget);
    expect(find.text('07:30 AM'), findsOneWidget);
    await tester.tap(find.text('View map'));
    await tester.pumpAndSettle();
    expect(find.byType(MapScreen), findsOneWidget);
    await tester.tap(find.byTooltip('Home'));
    await tester.pumpAndSettle();
    expect(find.byType(DashboardScreen), findsOneWidget);
    await tester.ensureVisible(find.byTooltip('Driver Profile'));
    await tester.tap(find.byTooltip('Driver Profile'));
    await tester.pumpAndSettle();
    expect(find.text('Sunil Fernando'), findsOneWidget);
    await tester.tap(find.byTooltip('Close'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Switch child  ▾'));
    await tester.tap(find.text('Switch child  ▾'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Amaya Perera'));
    await tester.pumpAndSettle();
    expect(find.text('Amaya Perera'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Driver attendance, student search and SOS preview are reachable', (tester) async {
    await start(tester);
    await tester.tap(find.text('Bus driver'));
    await tester.pumpAndSettle();
    expect(find.byType(DriverScreen), findsOneWidget);
    await tester.tap(find.text('Today’s Student Attendance'));
    await tester.pumpAndSettle();
    expect(find.byType(AttendanceScreen), findsOneWidget);
    expect(find.text('Absent'), findsWidgets);
    await tester.tap(find.byTooltip('Home'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Students'));
    await tester.tap(find.text('Students').first);
    // The label sits below the tappable tile; tap its semantic button instead.
    await tester.tap(find.bySemanticsLabel('Students').first);
    await tester.pumpAndSettle();
    expect(find.byType(StudentListScreen), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Amaya');
    await tester.pumpAndSettle();
    expect(find.text('Kavindu Perera'), findsNothing);
    await tester.tap(find.text('Amaya Perera'));
    await tester.pumpAndSettle();
    expect(find.byType(StudentProfileScreen), findsOneWidget);
    await tester.tap(find.byTooltip('Home'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('SOS'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Vehicle breakdown'));
    await tester.pumpAndSettle();
    expect(find.text('This is a UI preview. Emergency calls and alerts are not connected.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Adding a student validates and updates the shared list', (tester) async {
    tester.view.physicalSize = const Size(402, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final container = ProviderContainer();
    addTearDown(container.dispose);
    await tester.pumpWidget(UncontrolledProviderScope(container: container, child: const MaterialApp(home: AddStudentScreen(driver: true))));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Save student'));
    await tester.tap(find.text('Save student'));
    await tester.pumpAndSettle();
    expect(find.text('Please enter Student’s full name'), findsOneWidget);
    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'Test Student');
    await tester.enterText(fields.at(1), 'Colombo');
    await tester.enterText(fields.at(2), 'Test Parent');
    await tester.enterText(fields.at(3), '0771234567');
    await tester.ensureVisible(find.text('Save student'));
    await tester.tap(find.text('Save student'));
    await tester.pumpAndSettle();
    expect(container.read(transportStudentsProvider).last.name, 'Test Student');
  });

  for (final width in [320.0, 402.0, 600.0]) {
    testWidgets('Home screens fit a $width pixel viewport', (tester) async {
      tester.view.physicalSize = Size(width, 874);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      for (final screen in [const DashboardScreen(), const DriverScreen()]) {
        await tester.pumpWidget(ProviderScope(child: MaterialApp(home: screen)));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      }
    });
  }
}
