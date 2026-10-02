import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/api_client.dart';

class AuthService {
  AuthService(this._storage, this._apiClient);

  final FlutterSecureStorage _storage;
  final ApiClient _apiClient;

  Future<bool> login(String email, String password) async {
    try {
      final response = await _apiClient.dio.post('/auth/login', data: {'email': email, 'password': password});
      if (response.statusCode == 200) {
        final access = response.data['access_token'] as String;
        final refresh = response.data['refresh_token'] as String;
        await _storage.write(key: 'access_token', value: access);
        await _storage.write(key: 'refresh_token', value: refresh);
        return true;
      }
      return false;
    } on DioException {
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }
}
