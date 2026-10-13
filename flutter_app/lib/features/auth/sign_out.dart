import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import 'login_screen.dart';

Future<void> signOut(BuildContext context, WidgetRef ref) async {
  await ref.read(authStateProvider.notifier).logout();
  if (!context.mounted) return;
  Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(builder: (_) => const LoginScreen()),
      (_) => false);
}
