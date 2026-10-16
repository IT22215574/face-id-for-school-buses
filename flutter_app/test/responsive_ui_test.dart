import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/app_theme.dart';
import 'package:school_bus_parent_app/features/dashboard/dashboard_screen.dart';
import 'package:school_bus_parent_app/features/driver/driver_screen.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';

void main() {
  testWidgets('Home screens fit narrow phones with larger text',
      (tester) async {
    tester.view.physicalSize = const Size(320, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    for (final screen in [const DashboardScreen(), const DriverScreen()]) {
      await tester.pumpWidget(ProviderScope(
          overrides: [
            transportLoadProvider.overrideWith((ref) async {}),
            transportStudentsProvider.overrideWith((ref) => [
                  const TransportStudent(
                    name: 'Kavindu Perera',
                    grade: 'Grade 6',
                    school: 'Maliyadeva College',
                    driverName: 'Sam Driver',
                    plate: 'BUS-24',
                  )
                ]),
          ],
          child: MaterialApp(
              theme: buildAppTheme(),
              builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(context)
                      .copyWith(textScaler: const TextScaler.linear(1.4)),
                  child: child!),
              home: screen)));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
  });
}
