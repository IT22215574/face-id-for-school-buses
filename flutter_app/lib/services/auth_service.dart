import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../core/api_client.dart';

enum AccountRole { parent, driver, admin }

class AuthService {
  AuthService(this._storage, this._apiClient);
  final FlutterSecureStorage _storage;
  final ApiClient _apiClient;

  Future<AccountRole?> login(String email, String password) async {
    return _authenticate(
        '/auth/login', {'email': email.trim(), 'password': password});
  }

  Future<AccountRole?> register(
      String name, String phone, String email, String password) {
    return _authenticate('/auth/register', {
      'name': name.trim(),
      'phone': phone.trim(),
      'email': email.trim(),
      'password': password,
    });
  }

  Future<AccountRole?> _authenticate(
      String path, Map<String, String> data) async {
    try {
      final response = await _apiClient.dio.post(path, data: data);
      final access = response.data['access_token'] as String;
      final refresh = response.data['refresh_token'] as String;
      await _storage.write(key: 'access_token', value: access);
      await _storage.write(key: 'refresh_token', value: refresh);
      // Fetch the role from the authenticated backend, never infer it from email.
      final profile = await _apiClient.dio.get('/me');
      final role = switch (profile.data['role']) {
        'PARENT' => AccountRole.parent,
        'DRIVER' => AccountRole.driver,
        'ADMIN' => AccountRole.admin,
        _ => null,
      };
      if (role == null) await logout();
      return role;
    } catch (_) {
      await logout();
      rethrow;
    }
  }

  Future<void> logout() async {
    final refresh = await _storage.read(key: 'refresh_token');
    try {
      if (refresh != null) {
        await _apiClient.dio
            .post('/auth/logout', data: {'refresh_token': refresh});
      }
    } on DioException {
      // Always clear the local session, including when the API is unreachable.
    } finally {
      await _storage.delete(key: 'access_token');
      await _storage.delete(key: 'refresh_token');
    }
  }
}
