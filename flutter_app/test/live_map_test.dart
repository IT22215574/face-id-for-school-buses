import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart' as osm;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/map/live_map_screen.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';

void main() {
  for (final detailsFail in [false, true]) {
    testWidgets('Parent tracks GPS when optional details fail: $detailsFail',
        (tester) async {
      const channel = MethodChannel('school_bus/maps_configuration');
      tester.binding.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (_) async => false);
      addTearDown(() => tester.binding.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null));
      FlutterSecureStorage.setMockInitialValues({});
      final client = ApiClient(const FlutterSecureStorage());
      var locationReads = 0;
      client.dio.interceptors
          .add(InterceptorsWrapper(onRequest: (request, handler) {
        if (detailsFail &&
            (request.path.endsWith('/status') ||
                request.path.endsWith('/route') ||
                request.path.endsWith('/route-history'))) {
          handler.reject(DioException(
              requestOptions: request,
              response: Response(requestOptions: request, statusCode: 403),
              type: DioExceptionType.badResponse));
          return;
        }
        dynamic data;
        switch (request.path) {
          case '/me/transport':
            data = [
              {
                'id': 41,
                'name': 'First child',
                'bus_id': 6,
                'plate_no': 'OTHER'
              },
              {'id': 42, 'name': 'Aisha', 'bus_id': 7, 'plate_no': 'BUS-24'}
            ];
          case '/buses/7/route':
            data = {'stops': []};
          case '/students/42/status':
            data = {'status': 'ON_BUS'};
          case '/buses/7/route-history':
            data = {'points': []};
          case '/buses/7/live-location':
            locationReads++;
            data = {
              'lat': locationReads == 1 ? 7.4863 : 7.4873,
              'lng': 80.3647,
              'server_time': DateTime.now()
                  .toUtc()
                  .subtract(const Duration(minutes: 3))
                  .toIso8601String()
                  .replaceAll('Z', detailsFail ? '' : 'Z')
            };
          default:
            fail('Unexpected tracking request: ${request.path}');
        }
        handler.resolve(
            Response(requestOptions: request, data: data, statusCode: 200));
      }));
      await tester.pumpWidget(ProviderScope(overrides: [
        apiClientProvider.overrideWithValue(client),
        selectedChildProvider.overrideWith((ref) => 1),
      ], child: const MaterialApp(home: LiveMapScreen(driver: false))));
      await tester.pumpAndSettle();
      expect(
          find.textContaining(detailsFail
              ? 'Aisha · Boarding status unavailable'
              : 'Aisha · Last boarding event: on bus'),
          findsOneWidget);
      expect(find.textContaining('Bus location is stale'), findsOneWidget);
      expect(find.textContaining('7.48630, 80.36470'), findsOneWidget);
      expect(find.text('Start sharing'), findsNothing);
      expect(locationReads, 1);
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      expect(locationReads, 2);
      expect(find.textContaining('7.48730, 80.36470'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    }, variant: TargetPlatformVariant({TargetPlatform.iOS}));
  }

  for (final missingChannel in [false, true]) {
    testWidgets(
        'Missing iOS maps ${missingChannel ? 'channel' : 'key'} keeps tracking open',
        (tester) async {
      const channel = MethodChannel('school_bus/maps_configuration');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel,
          (_) async {
        if (missingChannel) throw MissingPluginException();
        return false;
      });
      addTearDown(() => tester.binding.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null));
      FlutterSecureStorage.setMockInitialValues({});
      final client = ApiClient(const FlutterSecureStorage());
      client.dio.interceptors
          .add(InterceptorsWrapper(onRequest: (request, handler) {
        handler.reject(DioException(
            requestOptions: request,
            response: Response(
                requestOptions: request,
                data: {'detail': 'No assigned bus'},
                statusCode: 404),
            type: DioExceptionType.badResponse));
      }));
      await tester.pumpWidget(ProviderScope(
        overrides: [apiClientProvider.overrideWithValue(client)],
        child: const MaterialApp(home: LiveMapScreen()),
      ));
      await tester.pumpAndSettle();
      expect(find.byType(GoogleMap), findsNothing);
      expect(find.byType(osm.FlutterMap), findsOneWidget);
      expect(find.text('OpenStreetMap contributors'), findsOneWidget);
      expect(tester.takeException(), isNull);
    }, variant: TargetPlatformVariant({TargetPlatform.iOS}));
  }
}
