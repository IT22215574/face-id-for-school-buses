import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/app.dart';
import 'package:school_bus_parent_app/features/dashboard/dashboard_screen.dart';
import 'package:school_bus_parent_app/features/driver/driver_screen.dart';
import 'package:school_bus_parent_app/features/notifications/notifications_screen.dart';
import 'package:school_bus_parent_app/features/transport/student_screens.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final loader = FontLoader('Roboto');
    loader.addFont(rootBundle.load('assets/fonts/Roboto-Regular.ttf'));
    loader.addFont(rootBundle.load('assets/fonts/Roboto-Medium.ttf'));
    await loader.load();
    final icons = FontLoader('MaterialIcons')
      ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
  });
  testWidgets(
      'Supporting screens render and exported previews match phone size',
      (tester) async {
    tester.view.physicalSize = const Size(402, 874);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final previousShadows = debugDisableShadows;
    debugDisableShadows = false;
    addTearDown(() => debugDisableShadows = previousShadows);
    final key = GlobalKey();
    await tester.pumpWidget(ProviderScope(overrides: [
      transportLoadProvider.overrideWith((ref) async {}),
      transportStudentsProvider.overrideWith((ref) => [
            const TransportStudent(
                name: 'Kavindu', school: 'Maliyadeva College, Kurunegala')
          ])
    ], child: RepaintBoundary(key: key, child: const SchoolBusParentApp())));
    await tester.pumpAndSettle();
    final theme = Theme.of(tester.element(find.text('School Bus Sign In')));
    final screens = <String, Widget>{
      'parent-home': const DashboardScreen(),
      'driver-home': const DriverScreen(),
      'select-child': const SelectChildScreen(),
      'student-details': const StudentListScreen(),
      'student-profile': const StudentProfileScreen(
          student: TransportStudent(name: 'Kavindu Perera')),
      'attendance': const AttendanceScreen(),
      'notifications': const NotificationsScreen(),
      'sos': const SosScreen(),
    };
    for (final entry in screens.entries) {
      await tester.pumpWidget(ProviderScope(
          overrides: [
            transportLoadProvider.overrideWith((ref) async {}),
            transportStudentsProvider.overrideWith((ref) => [
                  const TransportStudent(
                      name: 'Kavindu', school: 'Maliyadeva College, Kurunegala')
                ])
          ],
          child: RepaintBoundary(
              key: key,
              child: MaterialApp(
                  debugShowCheckedModeBanner: false,
                  theme: theme,
                  home: KeyedSubtree(
                      key: ValueKey(entry.key), child: entry.value)))));
      await tester.pumpAndSettle();
      await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 100)));
      await tester.pump();
      expect(tester.takeException(), isNull, reason: entry.key);
      if (const bool.fromEnvironment('CAPTURE_UI')) {
        await tester.runAsync(() async {
          final boundary =
              key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
          final image = await boundary.toImage();
          final data = await image.toByteData(format: ui.ImageByteFormat.png);
          final dir = Directory('build/ui-preview');
          await dir.create(recursive: true);
          await File('${dir.path}/${entry.key}.png')
              .writeAsBytes(data!.buffer.asUint8List());
          image.dispose();
        });
      }
    }
    debugDisableShadows = previousShadows;
  });
}
