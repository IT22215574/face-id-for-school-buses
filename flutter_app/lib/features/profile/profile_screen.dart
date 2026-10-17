import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../../providers/auth_provider.dart';
import '../auth/sign_out.dart';
import '../transport/transport_state.dart';

final accountProfileProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  ref.watch(authStateProvider);
  final response = await ref.read(apiClientProvider).dio.get('/me');
  return Map<String, dynamic>.from(response.data as Map);
});

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});
  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  bool _initialized = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_busy || !_form.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(apiClientProvider).dio.patch('/me', data: {
        'name': _name.text.trim(),
        'email': _email.text.trim(),
        'phone': _phone.text.trim(),
      });
      ref.invalidate(accountProfileProvider);
      ref.invalidate(transportLoadProvider);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Profile updated')));
      }
    } on DioException catch (e) {
      if (mounted) {
        setState(() => _error = e.response?.statusCode == 409
            ? 'That email or phone is already in use.'
            : 'Could not save your profile. Please try again.');
      }
    } catch (_) {
      if (mounted) {
        setState(
            () => _error = 'Could not save your profile. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(accountProfileProvider);
    return BusScaffold(
        title: 'My profile',
        child: profile.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => Column(children: [
            const Text('Could not load your profile.'),
            TextButton(
                onPressed: () => ref.invalidate(accountProfileProvider),
                child: const Text('Retry')),
            TextButton(
                onPressed: () => signOut(context, ref),
                child: const Text('Sign out')),
          ]),
          data: (account) {
            if (!_initialized) {
              _name.text = account['name'] as String;
              _email.text = account['email'] as String;
              _phone.text = account['phone'] as String;
              _initialized = true;
            }
            final driver = account['role'] == 'DRIVER';
            return Form(
                key: _form,
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(child: ProfileAvatar(driver: driver)),
                      const SizedBox(height: 12),
                      Text(driver ? 'Driver account' : 'Parent account',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                          driver
                              ? 'Manage your contact details. Add students to your vehicle from the home screen.'
                              : 'Manage your contact details. Your driver can add your child to their vehicle.',
                          textAlign: TextAlign.center),
                      const SizedBox(height: 24),
                      TextFormField(
                          controller: _name,
                          enabled: !_busy,
                          textCapitalization: TextCapitalization.words,
                          decoration: const InputDecoration(
                              labelText: 'Full name',
                              prefixIcon: Icon(Icons.person_outline)),
                          validator: (v) => (v?.trim().length ?? 0) < 2 ||
                                  v!.trim().length > 120
                              ? 'Enter a name between 2 and 120 characters'
                              : null),
                      const SizedBox(height: 16),
                      TextFormField(
                          controller: _email,
                          enabled: !_busy,
                          keyboardType: TextInputType.emailAddress,
                          autocorrect: false,
                          decoration: const InputDecoration(
                              labelText: 'Email',
                              prefixIcon: Icon(Icons.email_outlined)),
                          validator: (v) =>
                              RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                                      .hasMatch(v?.trim() ?? '')
                                  ? null
                                  : 'Enter a valid email address'),
                      const SizedBox(height: 16),
                      TextFormField(
                          controller: _phone,
                          enabled: !_busy,
                          keyboardType: TextInputType.phone,
                          decoration: const InputDecoration(
                              labelText: 'Phone number',
                              prefixIcon: Icon(Icons.phone_outlined)),
                          validator: (v) => (v?.trim().length ?? 0) < 8 ||
                                  v!.trim().length > 32
                              ? 'Enter a phone number between 8 and 32 characters'
                              : null),
                      const SizedBox(height: 24),
                      if (_error != null)
                        Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: Text(_error!,
                                style: const TextStyle(color: Colors.red))),
                      FilledButton.icon(
                          onPressed: _busy ? null : _save,
                          icon: const Icon(Icons.save_outlined),
                          label: Text(_busy ? 'Saving…' : 'Save changes')),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                          onPressed: _busy
                              ? null
                              : () async {
                                  setState(() => _busy = true);
                                  await signOut(context, ref);
                                },
                          icon: const Icon(Icons.logout),
                          label: const Text('Sign out')),
                    ]));
          },
        ));
  }
}
