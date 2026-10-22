import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../driver/driver_screen.dart';
import '../admin/admin_screen.dart';
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
  final nameController = TextEditingController();
  final phoneController = TextEditingController();
  final confirmController = TextEditingController();
  bool isRegistering = false;
  bool isLoading = false;
  bool hidePassword = true;
  String? error;
  @override
  void dispose() {
    nameController.dispose();
    phoneController.dispose();
    confirmController.dispose();
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
      final auth = ref.read(authStateProvider.notifier);
      if (isRegistering) {
        await auth.register(nameController.text, phoneController.text,
            emailController.text, passwordController.text);
      } else {
        await auth.login(emailController.text, passwordController.text);
      }
      if (!mounted) return;
      final role = ref.read(authStateProvider);
      if (role == null) {
        setState(() => error = 'Please use a parent, driver or admin account.');
        return;
      }
      Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute<void>(
              settings: const RouteSettings(name: 'transport-home'),
              builder: (_) => role == AccountRole.admin
                  ? const AdminScreen()
                  : role == AccountRole.driver
                      ? const DriverScreen()
                      : const SelectChildScreen()),
          (_) => false);
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => error = isRegistering &&
              [400, 409].contains(e.response?.statusCode)
          ? 'An account with this email or phone already exists. Please sign in.'
          : isRegistering && e.response?.statusCode == 422
              ? 'Please check your details. Passwords must be at least 8 characters and at most 72 bytes.'
              : e.response?.statusCode == 401
                  ? 'Invalid email or password.'
                  : e.response != null
                      ? '${isRegistering ? 'Signup' : 'Sign-in'} failed (server error ${e.response!.statusCode}). Please try again.'
                      : 'Cannot connect to the server. Please check the API is running.');
    } catch (_) {
      if (mounted) {
        setState(() => error =
            'Unable to ${isRegistering ? 'create account' : 'sign in'}. Please try again.');
      }
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      body: Container(
          decoration: const BoxDecoration(gradient: busSoftGradient),
          child: SafeArea(
              child: Center(
                  child: SingleChildScrollView(
                      padding: const EdgeInsets.all(24),
                      child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 400),
                          child: Form(
                              key: _formKey,
                              child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                        padding: const EdgeInsets.all(24),
                                        decoration: BoxDecoration(
                                            gradient: busGradient,
                                            borderRadius:
                                                BorderRadius.circular(28),
                                            boxShadow: const [
                                              BoxShadow(
                                                  color: Color(0x332563EB),
                                                  blurRadius: 28,
                                                  offset: Offset(0, 12))
                                            ]),
                                        child: const Icon(
                                            Icons.directions_bus_rounded,
                                            size: 48,
                                            color: Colors.white)),
                                    const SizedBox(height: 24),
                                    Text(
                                        isRegistering
                                            ? 'Parent Sign Up'
                                            : 'School Bus Sign In',
                                        style: const TextStyle(
                                            fontSize: 28,
                                            fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 12),
                                    Text(
                                        isRegistering
                                            ? 'Create your parent account. Your driver can then add your child using your registered email.'
                                            : 'Sign in with your parent, driver or admin account.',
                                        textAlign: TextAlign.center),
                                    const SizedBox(height: 32),
                                    if (isRegistering) ...[
                                      TextFormField(
                                        controller: nameController,
                                        enabled: !isLoading,
                                        autofillHints: const [
                                          AutofillHints.name
                                        ],
                                        decoration: const InputDecoration(
                                            labelText: 'Full name'),
                                        validator: (value) => (value
                                                            ?.trim()
                                                            .length ??
                                                        0) <
                                                    2 ||
                                                value!.trim().length > 120
                                            ? 'Enter your full name (2–120 characters)'
                                            : null,
                                      ),
                                      const SizedBox(height: 16),
                                      TextFormField(
                                        controller: phoneController,
                                        enabled: !isLoading,
                                        keyboardType: TextInputType.phone,
                                        autofillHints: const [
                                          AutofillHints.telephoneNumber
                                        ],
                                        decoration: const InputDecoration(
                                            labelText: 'Phone number'),
                                        validator: (value) => !RegExp(
                                                    r'^\+?[0-9]{8,15}$')
                                                .hasMatch(value?.trim() ?? '')
                                            ? 'Enter 8–15 digits, optionally starting with +'
                                            : null,
                                      ),
                                      const SizedBox(height: 16),
                                    ],
                                    TextFormField(
                                        controller: emailController,
                                        enabled: !isLoading,
                                        keyboardType:
                                            TextInputType.emailAddress,
                                        autocorrect: false,
                                        autofillHints: const [
                                          AutofillHints.username
                                        ],
                                        decoration: const InputDecoration(
                                            labelText: 'Email'),
                                        validator: (value) => value == null ||
                                                !value.trim().contains('@')
                                            ? 'Enter a valid email address'
                                            : null),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                        controller: passwordController,
                                        enabled: !isLoading,
                                        obscureText: hidePassword,
                                        autofillHints: const [
                                          AutofillHints.password
                                        ],
                                        decoration: InputDecoration(
                                            labelText: 'Password',
                                            suffixIcon: IconButton(
                                                tooltip: hidePassword
                                                    ? 'Show password'
                                                    : 'Hide password',
                                                onPressed: () => setState(() =>
                                                    hidePassword =
                                                        !hidePassword),
                                                icon: Icon(hidePassword
                                                    ? Icons.visibility_outlined
                                                    : Icons
                                                        .visibility_off_outlined))),
                                        validator: (value) => value == null ||
                                                value.isEmpty
                                            ? 'Enter your password'
                                            : isRegistering && value.length < 8
                                                ? 'Use at least 8 characters'
                                                : null,
                                        onFieldSubmitted: (_) => _login()),
                                    if (isRegistering) ...[
                                      const SizedBox(height: 16),
                                      TextFormField(
                                        controller: confirmController,
                                        enabled: !isLoading,
                                        obscureText: hidePassword,
                                        decoration: const InputDecoration(
                                            labelText: 'Confirm password'),
                                        validator: (value) =>
                                            value != passwordController.text
                                                ? 'Passwords do not match'
                                                : null,
                                        onFieldSubmitted: (_) => _login(),
                                      ),
                                    ],
                                    const SizedBox(height: 24),
                                    if (error != null) ...[
                                      Text(error!,
                                          style: const TextStyle(
                                              color: Colors.red),
                                          textAlign: TextAlign.center),
                                      const SizedBox(height: 16)
                                    ],
                                    SizedBox(
                                        width: double.infinity,
                                        child: FilledButton.icon(
                                            onPressed:
                                                isLoading ? null : _login,
                                            icon: const Icon(Icons.login),
                                            label: Text(isLoading
                                                ? (isRegistering
                                                    ? 'Creating account...'
                                                    : 'Signing in...')
                                                : (isRegistering
                                                    ? 'Create account'
                                                    : 'Sign in')))),
                                    TextButton(
                                      onPressed: isLoading
                                          ? null
                                          : () {
                                              _formKey.currentState?.reset();
                                              setState(() {
                                                isRegistering = !isRegistering;
                                                error = null;
                                              });
                                            },
                                      child: Text(isRegistering
                                          ? 'Already have an account? Sign in'
                                          : 'New parent? Sign up'),
                                    ),
                                  ]))))))));
}
