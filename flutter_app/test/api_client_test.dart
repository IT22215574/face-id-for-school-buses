import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/core/api_client.dart';

class SessionAdapter implements HttpClientAdapter {
  SessionAdapter(this.refreshStatus);
  final int refreshStatus;
  int renewals = 0;
  int profileRequests = 0;
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream,
      Future<void>? cancelFuture) async {
    int status;
    Map<String, dynamic> body;
    if (options.path == '/auth/refresh') {
      renewals++;
      expect(options.data, {'refresh_token': 'valid-refresh'});
      status = refreshStatus;
      body = {'access_token': 'new-access', 'refresh_token': 'new-refresh'};
    } else {
      expect(options.path, '/me');
      profileRequests++;
      status =
          options.headers['Authorization'] == 'Bearer new-access' ? 200 : 401;
      body = {'name': 'Test User'};
    }
    return ResponseBody.fromString(jsonEncode(body), status, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType]
    });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const storage = FlutterSecureStorage();
  setUp(() => FlutterSecureStorage.setMockInitialValues({
        'access_token': 'expired-access',
        'refresh_token': 'valid-refresh',
      }));
  test('Expired profile session renews and retries concurrent requests',
      () async {
    final client = ApiClient(storage);
    final adapter = SessionAdapter(200);
    client.dio.httpClientAdapter = adapter;
    final responses =
        await Future.wait([client.dio.get('/me'), client.dio.get('/me')]);
    expect(responses.every((response) => response.data['name'] == 'Test User'),
        isTrue);
    expect(adapter.renewals, 1);
    expect(await storage.read(key: 'access_token'), 'new-access');
    expect(await storage.read(key: 'refresh_token'), 'new-refresh');
  });
  for (final status in [401, 503]) {
    test('Refresh failure $status handles stored session correctly', () async {
      final client = ApiClient(storage);
      final adapter = SessionAdapter(status);
      client.dio.httpClientAdapter = adapter;
      await expectLater(client.dio.get('/me'), throwsA(isA<DioException>()));
      expect(adapter.renewals, 1);
      expect(adapter.profileRequests, 1);
      expect(await storage.read(key: 'refresh_token'),
          status == 401 ? isNull : 'valid-refresh');
    });
  }
}
