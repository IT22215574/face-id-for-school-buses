import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/services/auth_service.dart';

class AuthAdapter implements HttpClientAdapter {
  AuthAdapter(this.role);
  final String role;
  final paths = <String>[];
  @override
  Future<ResponseBody> fetch(RequestOptions options,
      Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    paths.add(options.path);
    final Map<String, Object> body;
    if (options.path == '/auth/login') {
      body = {'access_token': 'test-access', 'refresh_token': 'test-refresh'};
    } else {
      expect(options.path, '/me');
      expect(options.headers['Authorization'], 'Bearer test-access');
      body = {'role': role};
    }
    return ResponseBody.fromString(jsonEncode(body), 200, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType]
    });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final role in AccountRole.values) {
    test('Login retrieves ${role.name} role from the backend /me route',
        () async {
      FlutterSecureStorage.setMockInitialValues({});
      const storage = FlutterSecureStorage();
      final client = ApiClient(storage);
      final adapter = AuthAdapter(role.name.toUpperCase());
      client.dio.httpClientAdapter = adapter;
      final service = AuthService(storage, client);
      expect(await service.login('${role.name}@example.com', 'test-password'),
          role);
      expect(adapter.paths, ['/auth/login', '/me']);
      expect(await storage.read(key: 'access_token'), 'test-access');
    });
  }
}
