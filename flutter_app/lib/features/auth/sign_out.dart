import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import 'login_screen.dart';
import '../transport/transport_state.dart';
import '../profile/profile_screen.dart';

Future<void> signOut(BuildContext context, WidgetRef ref) async {
  await ref.read(authStateProvider.notifier).logout();
  ref.read(transportStudentsProvider.notifier).state = [];
  ref.read(selectedChildProvider.notifier).state = 0;
  ref.invalidate(accountProfileProvider);
  if (!context.mounted) return;
  Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(builder: (_) => const LoginScreen()),
      (_) => false);
}
