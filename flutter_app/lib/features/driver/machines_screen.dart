import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

final busMachinesProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  ref.watch(authStateProvider);
  final response =
      await ref.read(apiClientProvider).dio.get('/driver/machines');
  return Map<String, dynamic>.from(response.data as Map);
});

class MachinesScreen extends ConsumerWidget {
  const MachinesScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('Bus face ID machines')),
        body: ref.watch(busMachinesProvider).when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => Center(
                  child: TextButton(
                      onPressed: () => ref.invalidate(busMachinesProvider),
                      child: const Text(
                          'Could not load your assigned bus. Retry'))),
              data: (data) =>
                  ListView(padding: const EdgeInsets.all(20), children: [
                Text('Bus ${data['plate_no']}',
                    style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                const Text(
                    'Register one machine at each door. Scans at the boarding machine record “Got on”; scans at the exit machine record “Dropped off”.'),
                for (final role in ['ENTRY', 'EXIT'])
                  Builder(builder: (context) {
                    final matches = (data['machines'] as List)
                        .where((m) => m['role'] == role);
                    final machine = matches.isEmpty
                        ? null
                        : Map<String, dynamic>.from(matches.first as Map);
                    return Card(
                        margin: const EdgeInsets.only(top: 20),
                        child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                      role == 'ENTRY'
                                          ? 'Boarding machine'
                                          : 'Exit machine',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium),
                                  Text(machine == null
                                      ? 'Not registered'
                                      : '${machine['model']} · ${machine['serial']}'),
                                  if (machine != null)
                                    Text(machine['last_seen_at'] == null
                                        ? 'Waiting for first connection'
                                        : 'Last connected: ${DateTime.parse(machine['last_seen_at'] as String).toLocal()}'),
                                  const SizedBox(height: 8),
                                  FilledButton(
                                      onPressed: () => Navigator.of(context)
                                          .push(MaterialPageRoute<void>(
                                              builder: (_) => MachineEditor(
                                                  role: role,
                                                  machine: machine,
                                                  students: data['students']
                                                      as List))),
                                      child: Text(machine == null
                                          ? 'Register machine'
                                          : 'Edit student IDs')),
                                ])));
                  }),
                const SizedBox(height: 20),
                const Text(
                    'On both machines, set Cloud Server Address to your backend host and use the backend port (8000 for local testing). Enroll faces on each machine, then enter their enrolled user IDs here. Registering here does not enroll faces on the device.'),
                TextButton(
                    onPressed: () => ref.invalidate(busMachinesProvider),
                    child: const Text('Refresh connection status')),
              ]),
            ),
      );
}

class MachineEditor extends ConsumerStatefulWidget {
  const MachineEditor(
      {super.key,
      required this.role,
      required this.machine,
      required this.students});
  final String role;
  final Map<String, dynamic>? machine;
  final List students;
  @override
  ConsumerState<MachineEditor> createState() => _MachineEditorState();
}

class _MachineEditorState extends ConsumerState<MachineEditor> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _serial;
  late final TextEditingController _model;
  late final TextEditingController _zone;
  final Map<int, TextEditingController> _pins = {};
  bool _busy = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    _serial =
        TextEditingController(text: widget.machine?['serial'] as String? ?? '');
    _model =
        TextEditingController(text: widget.machine?['model'] as String? ?? '');
    _zone = TextEditingController(
        text: widget.machine?['timezone'] as String? ?? 'Asia/Colombo');
    final mapped = widget.machine?['students'] as Map? ?? {};
    for (final student in widget.students) {
      final id = student['id'] as int;
      final matches = mapped.entries.where((entry) => entry.value == id);
      _pins[id] = TextEditingController(
          text: matches.isEmpty ? '' : matches.first.key as String);
    }
  }

  Future<void> _save() async {
    if (_busy || !_form.currentState!.validate()) return;
    final students = <String, int>{};
    for (final entry in _pins.entries) {
      final pin = entry.value.text.trim();
      if (pin.isEmpty) continue;
      if (students.containsKey(pin)) {
        setState(
            () => _error = 'Each enrolled user ID must belong to one student.');
        return;
      }
      students[pin] = entry.key;
    }
    await _request(() => ref
            .read(apiClientProvider)
            .dio
            .put('/driver/machines/${widget.role}', data: {
          'serial': _serial.text.trim(),
          'model': _model.text.trim(),
          'timezone': _zone.text.trim(),
          'students': students,
        }));
  }

  Future<void> _request(Future<dynamic> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      ref.invalidate(busMachinesProvider);
      if (mounted) Navigator.of(context).pop();
    } on DioException catch (e) {
      if (!mounted) return;
      final data = e.response?.data;
      setState(() => _error = data is Map && data['detail'] is String
          ? data['detail'] as String
          : 'Could not save machine settings. Check the fields and connection.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _remove() async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
              title: const Text('Remove machine?'),
              content: const Text(
                  'This machine will stop sending attendance to this bus. Recorded scans are kept.'),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('Cancel')),
                TextButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: const Text('Remove'))
              ],
            ));
    if (confirmed == true && mounted) {
      await _request(() => ref
          .read(apiClientProvider)
          .dio
          .delete('/driver/machines/${widget.role}'));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title: Text(widget.role == 'ENTRY'
                ? 'Boarding machine setup'
                : 'Exit machine setup')),
        body: Form(
            key: _form,
            child: ListView(padding: const EdgeInsets.all(20), children: [
              TextFormField(
                  controller: _serial,
                  enabled: !_busy && widget.machine == null,
                  decoration:
                      const InputDecoration(labelText: 'Machine serial number'),
                  validator: (v) =>
                      RegExp(r'^[A-Za-z0-9_-]{1,40}$').hasMatch(v?.trim() ?? '')
                          ? null
                          : 'Enter the serial number from the machine'),
              const SizedBox(height: 16),
              TextFormField(
                  controller: _model,
                  enabled: !_busy,
                  decoration: const InputDecoration(labelText: 'ZKTeco model'),
                  maxLength: 100,
                  validator: (v) =>
                      (v?.trim().isEmpty ?? true) ? 'Enter the model' : null),
              TextFormField(
                  controller: _zone,
                  enabled: !_busy && widget.machine == null,
                  decoration:
                      const InputDecoration(labelText: 'Machine timezone')),
              const SizedBox(height: 20),
              const Text('Enrolled user IDs',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              const Text(
                  'Match each student to the user ID enrolled on this machine. Leave blank if not enrolled. IDs can differ between the two machines.'),
              if (widget.students.isEmpty)
                const Text(
                    'Add students to your bus first. You can save the machine and map IDs later.'),
              for (final student in widget.students)
                Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: TextFormField(
                      controller: _pins[student['id']],
                      enabled: !_busy,
                      decoration: InputDecoration(
                          labelText:
                              '${student['name']} · Grade ${student['grade']}'),
                      validator: (v) => (v?.trim().length ?? 0) > 32 ||
                              RegExp(r'\s').hasMatch(v?.trim() ?? '')
                          ? 'Use an ID without spaces, up to 32 characters'
                          : null,
                    )),
              if (_error != null)
                Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Text(_error!,
                        style: const TextStyle(color: Colors.red))),
              const SizedBox(height: 20),
              FilledButton(
                  onPressed: _busy ? null : _save,
                  child: Text(_busy ? 'Saving…' : 'Save machine')),
              if (widget.machine != null)
                TextButton(
                    onPressed: _busy ? null : _remove,
                    child: const Text('Remove machine')),
            ])),
      );

  @override
  void dispose() {
    _serial.dispose();
    _model.dispose();
    _zone.dispose();
    for (final controller in _pins.values) {
      controller.dispose();
    }
    super.dispose();
  }
}
