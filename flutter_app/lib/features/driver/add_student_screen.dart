import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../../providers/auth_provider.dart';
import '../transport/transport_state.dart';

final driverVehicleProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  ref.watch(authStateProvider);
  final response = await ref.read(apiClientProvider).dio.get('/driver/bus');
  return Map<String, dynamic>.from(response.data as Map);
});

class AddStudentScreen extends ConsumerStatefulWidget {
  const AddStudentScreen({super.key});
  @override
  ConsumerState<AddStudentScreen> createState() => _AddStudentScreenState();
}

class _AddStudentScreenState extends ConsumerState<AddStudentScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _grade = TextEditingController();
  final _parentEmail = TextEditingController();
  final _fatherPhone = TextEditingController();
  final _motherPhone = TextEditingController();
  String? _school;
  String? _error;
  bool _saving = false;

  @override
  void dispose() {
    _name.dispose();
    _grade.dispose();
    _parentEmail.dispose();
    _fatherPhone.dispose();
    _motherPhone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving || !_form.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref.read(apiClientProvider).dio.post('/driver/students', data: {
        'name': _name.text.trim(),
        'grade': _grade.text.trim(),
        'school_id': _school,
        'parent_email': _parentEmail.text.trim().toLowerCase(),
        'father_phone': _fatherPhone.text.trim(),
        'mother_phone': _motherPhone.text.trim(),
      });
      ref.invalidate(transportLoadProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Student added to your vehicle')));
      Navigator.of(context).pop();
    } on DioException catch (error) {
      if (!mounted) return;
      final data = error.response?.data;
      setState(() => _error = data is Map && data['detail'] is String
          ? data['detail'] as String
          : 'Could not add the student. Please try again.');
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Could not add the student. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final vehicle = ref.watch(driverVehicleProvider);
    return BusScaffold(
        title: 'Add student',
        child: vehicle.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => Column(children: [
            const Text(
                'Could not load your vehicle. You need an active vehicle to add students.'),
            TextButton(
                onPressed: () => ref.invalidate(driverVehicleProvider),
                child: const Text('Retry')),
          ]),
          data: (bus) => Form(
              key: _form,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  BusCard(
                      child: ListTile(
                    leading: const Icon(Icons.directions_bus, color: busBlue),
                    title: Text(bus['plate_no'] as String),
                    subtitle: Text(bus['route_name'] as String),
                  )),
                  const SizedBox(height: 16),
                  const Text(
                      'Add a child to this vehicle. Use the parent’s registered email so they can follow their child’s journey.'),
                  const SizedBox(height: 24),
                  TextFormField(
                      controller: _name,
                      enabled: !_saving,
                      textCapitalization: TextCapitalization.words,
                      maxLength: 120,
                      decoration:
                          const InputDecoration(labelText: 'Child’s full name'),
                      validator: (value) => (value?.trim().length ?? 0) < 2
                          ? 'Enter the child’s full name'
                          : null),
                  const SizedBox(height: 16),
                  TextFormField(
                      controller: _grade,
                      enabled: !_saving,
                      maxLength: 30,
                      decoration:
                          const InputDecoration(labelText: 'Grade / class'),
                      validator: (value) => (value?.trim().isEmpty ?? true)
                          ? 'Enter the grade or class'
                          : null),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'School'),
                      items: const [
                        DropdownMenuItem(
                            value: 'KUR-MALIYADEVA',
                            child: Text('Maliyadeva College',
                                overflow: TextOverflow.ellipsis)),
                        DropdownMenuItem(
                            value: 'KUR-MALIYADEVA-BALIKA',
                            child: Text('Maliyadeva Balika Vidyalaya',
                                overflow: TextOverflow.ellipsis)),
                      ],
                      onChanged: _saving
                          ? null
                          : (value) => setState(() => _school = value),
                      validator: (value) =>
                          value == null ? 'Choose a school' : null),
                  const SizedBox(height: 16),
                  TextFormField(
                      controller: _parentEmail,
                      enabled: !_saving,
                      keyboardType: TextInputType.emailAddress,
                      autocorrect: false,
                      decoration: const InputDecoration(
                          labelText: 'Parent’s registered email'),
                      validator: (value) =>
                          RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                                  .hasMatch(value?.trim() ?? '')
                              ? null
                              : 'Enter a valid parent email'),
                  const SizedBox(height: 24),
                  for (final contact in [
                    (_fatherPhone, 'Father’s mobile number (optional)'),
                    (_motherPhone, 'Mother’s mobile number (optional)'),
                  ]) ...[
                    TextFormField(
                        controller: contact.$1,
                        enabled: !_saving,
                        keyboardType: TextInputType.phone,
                        maxLength: 32,
                        decoration: InputDecoration(
                            labelText: contact.$2,
                            prefixIcon: const Icon(Icons.phone_outlined)),
                        validator: (value) =>
                            RegExp(r'^(?:|\+?[0-9][0-9 ()-]{6,30}[0-9])$')
                                    .hasMatch(value?.trim() ?? '')
                                ? null
                                : 'Enter a valid mobile number'),
                    const SizedBox(height: 16),
                  ],
                  if (_error != null)
                    Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Text(_error!,
                            style: const TextStyle(color: Colors.red))),
                  FilledButton.icon(
                      onPressed: _saving ? null : _save,
                      icon: const Icon(Icons.person_add_alt_1),
                      label: Text(_saving ? 'Adding…' : 'Add to my vehicle')),
                ],
              )),
        ));
  }
}
