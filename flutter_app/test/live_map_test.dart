import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/map/live_map_screen.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

void main() {
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
      expect(find.textContaining('The map is unavailable'), findsOneWidget);
      expect(tester.takeException(), isNull);
    }, variant: TargetPlatformVariant({TargetPlatform.iOS}));
  }
}
