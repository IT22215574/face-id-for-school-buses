import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'constants.dart';

class ApiClient {
  ApiClient(this._storage);

  final FlutterSecureStorage _storage;
  Future<void>? _refreshing;

  Future<void> _clearSession() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<void> _refreshSession() async {
    final refresh = await _storage.read(key: 'refresh_token');
    if (refresh == null || refresh.isEmpty) {
      await _clearSession();
      return;
    }
    final response =
        await _dio.post('/auth/refresh', data: {'refresh_token': refresh});
    await _storage.write(
        key: 'access_token', value: response.data['access_token'] as String);
    await _storage.write(
        key: 'refresh_token', value: response.data['refresh_token'] as String);
  }

  Dio get dio => _dio;

  late final Dio _dio = Dio(
    BaseOptions(
      baseUrl: AppConstants.baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ),
  )..interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.read(key: 'access_token');
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode != 401 ||
              error.requestOptions.path.startsWith('/auth/')) {
            handler.next(error);
            return;
          }
          final request = error.requestOptions;
          if (request.extra['sessionRetried'] == true) {
            await _clearSession();
            handler.next(error);
            return;
          }
          try {
            // Share renewal across simultaneous requests; refresh tokens rotate.
            final currentToken = await _storage.read(key: 'access_token');
            if (currentToken == null ||
                request.headers['Authorization'] == 'Bearer $currentToken') {
              final refresh = _refreshing ??= _refreshSession();
              try {
                await refresh;
              } finally {
                if (identical(_refreshing, refresh)) _refreshing = null;
              }
            }
            final token = await _storage.read(key: 'access_token');
            if (token == null) {
              handler.next(error);
              return;
            }
            request.extra['sessionRetried'] = true;
            request.headers['Authorization'] = 'Bearer $token';
            handler.resolve(await _dio.fetch<dynamic>(request));
          } on DioException catch (refreshError) {
            if (refreshError.response?.statusCode == 401 ||
                refreshError.response?.statusCode == 403) {
              await _clearSession();
            }
            handler.next(refreshError);
          } catch (_) {
            handler.next(error);
          }
        },
      ),
    );
}
