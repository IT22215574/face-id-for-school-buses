import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../driver/driver_screen.dart';
import '../transport/student_screens.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  bool isLoading = false;
  String? error;
  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (isLoading || !_formKey.currentState!.validate()) return;
    setState(() {
      isLoading = true;
      error = null;
    });
    try {
      await ref
          .read(authStateProvider.notifier)
          .login(emailController.text, passwordController.text);
      if (!mounted) return;
      final role = ref.read(authStateProvider);
      if (role == null) {
        setState(() => error = 'Please use a parent or driver account.');
        return;
      }
      Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute<void>(
              settings: const RouteSettings(name: 'transport-home'),
              builder: (_) => role == AccountRole.driver
                  ? const DriverScreen()
                  : const SelectChildScreen()),
          (_) => false);
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => error = e.response?.statusCode == 401
          ? 'Invalid email or password.'
          : e.response != null
              ? 'Sign-in failed (server error ${e.response!.statusCode}). Please try again.'
              : 'Cannot connect to the server. Please check the API is running.');
    } catch (_) {
      if (mounted) {
        setState(() => error = 'Unable to sign in. Please try again.');
      }
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      body: SafeArea(
          child: Center(
              child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 400),
                      child: Form(
                          key: _formKey,
                          child:
                              Column(mainAxisSize: MainAxisSize.min, children: [
                            const Icon(Icons.directions_bus,
                                size: 72, color: busBlue),
                            const SizedBox(height: 24),
                            const Text('School Bus Sign In',
                                style: TextStyle(
                                    fontSize: 28, fontWeight: FontWeight.bold)),
                            const SizedBox(height: 12),
                            const Text(
                                'Sign in with your parent or driver account.',
                                textAlign: TextAlign.center),
                            const SizedBox(height: 32),
                            TextFormField(
                                controller: emailController,
                                enabled: !isLoading,
                                keyboardType: TextInputType.emailAddress,
                                autocorrect: false,
                                autofillHints: const [AutofillHints.username],
                                decoration:
                                    const InputDecoration(labelText: 'Email'),
                                validator: (value) =>
                                    value == null || !value.trim().contains('@')
                                        ? 'Enter a valid email address'
                                        : null),
                            const SizedBox(height: 16),
                            TextFormField(
                                controller: passwordController,
                                enabled: !isLoading,
                                obscureText: true,
                                autofillHints: const [AutofillHints.password],
                                decoration: const InputDecoration(
                                    labelText: 'Password'),
                                validator: (value) =>
                                    value == null || value.isEmpty
                                        ? 'Enter your password'
                                        : null,
                                onFieldSubmitted: (_) => _login()),
                            const SizedBox(height: 24),
                            if (error != null) ...[
                              Text(error!,
                                  style: const TextStyle(color: Colors.red),
                                  textAlign: TextAlign.center),
                              const SizedBox(height: 16)
                            ],
                            SizedBox(
                                width: double.infinity,
                                child: FilledButton.icon(
                                    onPressed: isLoading ? null : _login,
                                    icon: const Icon(Icons.login),
                                    label: Text(isLoading
                                        ? 'Signing in...'
                                        : 'Login'))),
                          ])))))));
}
