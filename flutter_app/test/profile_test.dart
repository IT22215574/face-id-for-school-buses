import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/profile/profile_screen.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';

class ProfileAdapter implements HttpClientAdapter {
  ProfileAdapter(this.role);
  final String role;
  Map<String, dynamic>? saved;
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream,
      Future<void>? cancelFuture) async {
    expect(options.path, '/me');
    if (options.method == 'PATCH') saved = Map<String, dynamic>.from(options.data as Map);
    return ResponseBody.fromString(jsonEncode({
      'name': 'Test User', 'email': 'test@example.com', 'phone': '0711234567',
      ...?saved, 'role': role,
    }), 200, headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});
  }
  @override
  void close({bool force = false}) {}
}

void main() {
  for (final role in ['PARENT', 'DRIVER']) {
    testWidgets('$role profile loads, validates and saves contact details', (tester) async {
      FlutterSecureStorage.setMockInitialValues({});
      final client = ApiClient(const FlutterSecureStorage());
      final adapter = ProfileAdapter(role);
      client.dio.httpClientAdapter = adapter;
      await tester.pumpWidget(ProviderScope(overrides: [
        apiClientProvider.overrideWithValue(client),
        transportLoadProvider.overrideWith((ref) async {}),
      ], child: const MaterialApp(home: ProfileScreen())));
      await tester.pumpAndSettle();
      expect(find.text(role == 'DRIVER' ? 'Driver account' : 'Parent account'), findsOneWidget);
      await tester.enterText(find.byType(TextFormField).at(0), ' ');
      await tester.ensureVisible(find.text('Save changes'));
      await tester.tap(find.text('Save changes'));
      await tester.pumpAndSettle();
      expect(adapter.saved, isNull);
      await tester.enterText(find.byType(TextFormField).at(0), 'New Name');
      await tester.ensureVisible(find.text('Save changes'));
      await tester.tap(find.text('Save changes'));
      await tester.pumpAndSettle();
      expect(adapter.saved?['name'], 'New Name');
      expect(find.text('Profile updated'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}
