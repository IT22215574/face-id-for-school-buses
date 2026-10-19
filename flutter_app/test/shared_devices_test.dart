import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/features/tracking/shared_devices_screen.dart';

void main() {
  testWidgets('Missing Maps and Firebase configuration leaves usable guidance', (tester) async {
    const channel = MethodChannel('school_bus/maps_configuration');
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel, (_) async => false);
    addTearDown(() => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel, null));
    await tester.pumpWidget(const ProviderScope(child: MaterialApp(home: SharedDevicesScreen())));
    await tester.pumpAndSettle();
    expect(find.textContaining('Google Maps is not configured'), findsOneWidget);
    await tester.tap(find.text('Connect location sharing'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Configure Firebase using the tracking setup guide'), findsOneWidget);
    expect(find.text('Start sharing'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
