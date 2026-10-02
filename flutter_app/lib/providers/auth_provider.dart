import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/api_client.dart';
import '../services/auth_service.dart';

final secureStorageProvider = Provider((ref) => const FlutterSecureStorage());

final apiClientProvider = Provider((ref) => ApiClient(ref.read(secureStorageProvider)));

final authServiceProvider = Provider((ref) => AuthService(ref.read(secureStorageProvider), ref.read(apiClientProvider)));

// Temporary switch used to bypass the sign-in flow while the app is being checked.
const bool disableSignInPageForNow = true;

final authStateProvider = StateNotifierProvider<AuthController, bool>((ref) {
  return AuthController(ref.read(authServiceProvider));
});

class AuthController extends StateNotifier<bool> {
  AuthController(this._authService) : super(false);

  final AuthService _authService;

  Future<void> login(String email, String password) async {
    state = await _authService.login(email, password);
  }

  Future<void> logout() async {
    await _authService.logout();
    state = false;
  }
}
