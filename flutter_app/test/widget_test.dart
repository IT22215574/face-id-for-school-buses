import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/dashboard/dashboard_screen.dart';
import 'package:school_bus_parent_app/features/driver/driver_screen.dart';
import 'package:school_bus_parent_app/features/transport/student_screens.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

void main() {
  Future<void> show(
      WidgetTester tester, Widget screen, List<dynamic> children) async {
    FlutterSecureStorage.setMockInitialValues({});
    final client = ApiClient(const FlutterSecureStorage());
    client.dio.interceptors
        .add(InterceptorsWrapper(onRequest: (request, handler) {
      handler.resolve(
          Response(requestOptions: request, data: children, statusCode: 200));
    }));
    await tester.pumpWidget(ProviderScope(
        overrides: [apiClientProvider.overrideWithValue(client)],
        child: MaterialApp(home: screen)));
    await tester.pumpAndSettle();
  }

  final children = [
    {
      'id': 42,
      'name': 'Aisha',
      'grade': '5',
      'school': {'name': 'Maliyadeva Balika Vidyalaya, Kurunegala'},
      'bus_id': 7,
      'plate_no': 'BUS-24',
      'driver_name': 'Sam Driver',
      'driver_phone': '0771234567',
      'parent': 'Jane',
      'phone': '0777654321'
    },
    {
      'id': 43,
      'name': 'Kavindu',
      'grade': '6',
      'school': {'name': 'Maliyadeva College, Kurunegala'},
      'bus_id': 7,
      'plate_no': 'BUS-24',
      'driver_name': 'Sam Driver',
      'driver_phone': '0771234567',
      'parent': 'Jane',
      'phone': '0777654321'
    },
  ];
  testWidgets('Parent selects saved children and sees assigned driver',
      (tester) async {
    await show(tester, const SelectChildScreen(), children);
    expect(find.text('Aisha'), findsOneWidget);
    await tester.tap(find.byTooltip('Kavindu'));
    await tester.pumpAndSettle();
    expect(find.byType(DashboardScreen), findsOneWidget);
    expect(find.text('Kavindu'), findsOneWidget);
    await tester.ensureVisible(find.byTooltip('Driver Profile'));
    await tester.tap(find.byTooltip('Driver Profile'));
    await tester.pumpAndSettle();
    expect(find.text('Sam Driver'), findsOneWidget);
    expect(find.descendant(of: find.byType(BottomSheet), matching: find.text('BUS-24')), findsOneWidget);
    Navigator.of(tester.element(find.byType(BottomSheet))).pop();
    await tester.pumpAndSettle();
    for (final name in ['Aisha', 'Kavindu']) {
      await tester.ensureVisible(find.text('Switch child'));
      await tester.tap(find.text('Switch child'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip(name));
      await tester.pumpAndSettle();
      expect(find.byType(DashboardScreen, skipOffstage: false), findsOneWidget);
      expect(find.text(name), findsOneWidget);
    }
    expect(tester.takeException(), isNull);
  });
  testWidgets('Parent with no assigned children sees an empty state',
      (tester) async {
    await show(tester, const DashboardScreen(), []);
    expect(find.textContaining('No children assigned'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Driver sees saved students and real bus assignment',
      (tester) async {
    await show(tester, const DriverScreen(), children);
    expect(find.textContaining('Sam Driver'), findsOneWidget);
    expect(find.textContaining('2 assigned students'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
