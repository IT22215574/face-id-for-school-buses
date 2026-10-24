import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import '../../providers/auth_provider.dart';
import '../auth/sign_out.dart';
import 'face_devices_screen.dart';

class AdminScreen extends ConsumerStatefulWidget {
  const AdminScreen({super.key});
  @override
  ConsumerState<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends ConsumerState<AdminScreen> {
  List<dynamic> drivers = [], buses = [];
  bool loading = true;
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final api = ref.read(apiClientProvider).dio;
      final results = await Future.wait(
          [api.get('/admin/driver-registrations'), api.get('/admin/buses')]);
      if (mounted) {
        setState(() {
          drivers = results[0].data as List;
          buses = results[1].data as List;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
            () => error = 'Unable to load drivers and routes. Please retry.');
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> viewDriver(int id) async {
    try {
      final response = await ref
          .read(apiClientProvider)
          .dio
          .get('/admin/driver-registrations/$id');
      if (!mounted) return;
      final data = Map<String, dynamic>.from(response.data as Map);
      List<Widget> person(Map<String, dynamic> p) => [
            for (final key in [
              'name',
              'phone',
              'email',
              'nic',
              'license_no',
              'address'
            ])
              if (p[key] != null)
                ListTile(
                    title: Text(key.replaceAll('_', ' ').toUpperCase()),
                    subtitle: Text(p[key].toString())),
            for (final key in ['id_front', 'id_back', 'license_front'])
              if (p[key] != null) ...[
                Text(key == 'license_front'
                    ? 'Driving licence front'
                    : key == 'id_front'
                        ? 'ID front'
                        : 'ID back'),
                Image.memory(base64Decode((p[key] as String).split(',').last),
                    height: 180,
                    errorBuilder: (_, __, ___) =>
                        const Text('Photo unavailable')),
              ],
          ];
      await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
                  title: const Text('Driver registration'),
                  content: SizedBox(
                      width: 560,
                      child: SingleChildScrollView(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                            ...person(data),
                            if (data['assistant'] != null) ...[
                              const Divider(),
                              const Text('Assistant'),
                              ...person(Map<String, dynamic>.from(
                                  data['assistant'] as Map))
                            ],
                          ]))),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Close'))
                  ]));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Unable to load driver details.')));
      }
    }
  }

  Future<void> editDriver(int id) async {
    try {
      final response = await ref
          .read(apiClientProvider)
          .dio
          .get('/admin/driver-registrations/$id');
      if (!mounted) return;
      final saved = await Navigator.of(context).push<bool>(MaterialPageRoute(
          builder: (_) => DriverRegistrationScreen(
              buses: buses,
              existing: Map<String, dynamic>.from(response.data as Map))));
      if (saved == true && mounted) load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Unable to load driver for editing. Please retry.')));
      }
    }
  }

  Future<void> deleteRecord(String kind, int id, String label) async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
                title: Text('Delete $label?'),
                content: Text(
                    'This cannot be undone.${kind == 'driver-registrations' ? ' The driver login will also be removed.' : ''}'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Cancel')),
                  FilledButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('Delete'))
                ]));
    if (confirmed != true || !mounted) return;
    try {
      await ref.read(apiClientProvider).dio.delete('/admin/$kind/$id');
      if (mounted) {
        setState(() {
          if (kind == 'buses') {
            buses.removeWhere((b) => b['id'] == id);
          } else {
            drivers.removeWhere((d) => d['id'] == id);
          }
        });
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Deleted successfully.')));
      }
    } catch (e) {
      final detail = e is DioException && e.response?.data is Map
          ? e.response?.data['detail']
          : null;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(detail is String
                ? detail
                : 'Unable to delete. Please retry.')));
      }
    }
  }

  Future<void> saveBus([Map<String, dynamic>? existing]) async {
    final formKey = GlobalKey<FormState>();
    final plate = TextEditingController(text: existing?['plate_no'] as String?),
        device = TextEditingController(text: existing?['device_id'] as String?),
        route = TextEditingController(text: existing?['route_name'] as String?);
    bool busy = false;
    String? failure;
    final saved = await showDialog<bool>(
        context: context,
        builder: (context) => StatefulBuilder(
            builder: (context, update) => AlertDialog(
                  title: Text(existing == null
                      ? 'Create bus & route'
                      : 'Edit bus & route'),
                  content: Form(
                      key: formKey,
                      child: SingleChildScrollView(
                          child:
                              Column(mainAxisSize: MainAxisSize.min, children: [
                        for (final item in [
                          (plate, 'Registration plate', 32),
                          (device, 'Device identifier', 64),
                          (route, 'Route / destinations', 120)
                        ])
                          TextFormField(
                              controller: item.$1,
                              enabled: !busy,
                              maxLength: item.$3,
                              decoration: InputDecoration(labelText: item.$2),
                              validator: (v) => (v ?? '').trim().length < 2
                                  ? 'Enter at least two characters'
                                  : null),
                        if (failure != null) Text(failure!),
                      ]))),
                  actions: [
                    TextButton(
                        onPressed: busy ? null : () => Navigator.pop(context),
                        child: const Text('Cancel')),
                    FilledButton(
                        onPressed: busy
                            ? null
                            : () async {
                                if (!formKey.currentState!.validate()) return;
                                update(() => busy = true);
                                try {
                                  final api = ref.read(apiClientProvider).dio;
                                  final data = {
                                    'plate_no': plate.text.trim(),
                                    'device_id': device.text.trim(),
                                    'route_name': route.text.trim()
                                  };
                                  final response = existing == null
                                      ? await api.post('/admin/buses',
                                          data: data)
                                      : await api.put(
                                          '/admin/buses/${existing['id']}',
                                          data: data);
                                  if (mounted) {
                                    setState(() {
                                      final savedBus =
                                          Map<String, dynamic>.from(
                                              response.data as Map);
                                      buses = [
                                        savedBus,
                                        ...buses.where((bus) =>
                                            bus['id'] != savedBus['id'])
                                      ];
                                    });
                                  }
                                  if (context.mounted) {
                                    Navigator.pop(context, true);
                                  }
                                } catch (e) {
                                  if (context.mounted) {
                                    update(() {
                                      busy = false;
                                      final detail = e is DioException &&
                                              e.response?.data is Map
                                          ? e.response?.data['detail']
                                          : null;
                                      failure = detail is String
                                          ? detail
                                          : 'Unable to save bus and route. Please retry.';
                                    });
                                  }
                                }
                              },
                        child: Text(busy ? 'Saving…' : 'Save bus & route'))
                  ],
                )));
    await Future<void>.delayed(const Duration(milliseconds: 300));
    plate.dispose();
    device.dispose();
    route.dispose();
    if (saved == true && mounted) load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Super Admin'), actions: [
          IconButton(
              tooltip: 'Refresh',
              onPressed: load,
              icon: const Icon(Icons.refresh)),
          IconButton(
              tooltip: 'Sign out',
              onPressed: () => signOut(context, ref),
              icon: const Icon(Icons.logout))
        ]),
        floatingActionButton: FloatingActionButton.extended(
            onPressed: loading || error != null
                ? null
                : () async {
                    final saved = await Navigator.of(context).push<bool>(
                        MaterialPageRoute(
                            builder: (_) =>
                                DriverRegistrationScreen(buses: buses)));
                    if (saved == true) load();
                  },
            icon: const Icon(Icons.person_add),
            label: const Text('Create driver')),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : error != null
                ? Center(
                    child: TextButton(onPressed: load, child: Text(error!)))
                : ListView(
                    padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
                    children: [
                        ListTile(
                            leading: const Icon(Icons.face),
                            title: const Text('Face Recognition Devices'),
                            onTap: () => Navigator.of(context).push(
                                MaterialPageRoute<void>(
                                    builder: (_) =>
                                        const FaceDevicesScreen()))),
                        Text('Drivers & bus assignments',
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                            onPressed: () => saveBus(),
                            icon: const Icon(Icons.add_road),
                            label: const Text('Create bus & route')),
                        Text('Saved buses & routes (${buses.length})',
                            style: Theme.of(context).textTheme.titleLarge),
                        if (buses.isEmpty)
                          const Padding(
                              padding: EdgeInsets.all(16),
                              child: Text(
                                  'No routes saved yet. Create a bus and route to get started.')),
                        for (final bus in buses)
                          Card(
                              child: ListTile(
                                  leading: const Icon(Icons.route),
                                  title: Text(bus['route_name'] as String),
                                  subtitle: Text(
                                      '${bus['plate_no']}\nDevice: ${bus['device_id']}'),
                                  isThreeLine: true,
                                  trailing: PopupMenuButton<String>(
                                      tooltip: 'Route actions',
                                      onSelected: (action) {
                                        if (action == 'edit') {
                                          saveBus(Map<String, dynamic>.from(
                                              bus as Map));
                                        } else {
                                          deleteRecord(
                                              'buses',
                                              bus['id'] as int,
                                              bus['route_name'] as String);
                                        }
                                      },
                                      itemBuilder: (_) => const [
                                            PopupMenuItem(
                                                value: 'edit',
                                                child: Text('Edit')),
                                            PopupMenuItem(
                                                value: 'delete',
                                                child: Text('Delete'))
                                          ]))),
                        const SizedBox(height: 24),
                        const Text(
                            'Create driver login accounts, assign their bus and route, and register an optional assistant.'),
                        if (drivers.isEmpty)
                          const Padding(
                              padding: EdgeInsets.all(32),
                              child: Text('No drivers registered yet.')),
                        for (final driver in drivers)
                          Card(
                              child: ListTile(
                                  onTap: () => viewDriver(driver['id'] as int),
                                  leading: const Icon(Icons.directions_bus),
                                  title: Text(driver['name'] as String),
                                  subtitle: Text(
                                      '${driver['email']} · ${driver['phone']}\n${driver['plate_no'] ?? 'Unassigned'} · ${driver['route_name'] ?? 'No route'}'),
                                  isThreeLine: true,
                                  trailing: PopupMenuButton<String>(
                                      tooltip: 'Driver actions',
                                      onSelected: (action) {
                                        if (action == 'edit') {
                                          editDriver(driver['id'] as int);
                                        } else {
                                          deleteRecord(
                                              'driver-registrations',
                                              driver['id'] as int,
                                              driver['name'] as String);
                                        }
                                      },
                                      itemBuilder: (_) => const [
                                            PopupMenuItem(
                                                value: 'edit',
                                                child: Text('Edit')),
                                            PopupMenuItem(
                                                value: 'delete',
                                                child: Text('Delete'))
                                          ]))),
                      ]),
      );
}

class DriverRegistrationScreen extends ConsumerStatefulWidget {
  const DriverRegistrationScreen(
      {super.key, required this.buses, this.existing});
  final Map<String, dynamic>? existing;
  final List<dynamic> buses;
  @override
  ConsumerState<DriverRegistrationScreen> createState() =>
      _DriverRegistrationScreenState();
}

class _DriverRegistrationScreenState
    extends ConsumerState<DriverRegistrationScreen> {
  final form = GlobalKey<FormState>();
  final fields = <String, TextEditingController>{};
  final photos = <String, String>{};
  bool assistant = false, saving = false;
  int? busId;
  String? error;
  TextEditingController controller(String key) =>
      fields.putIfAbsent(key, TextEditingController.new);
  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    if (existing == null) return;
    void fill(Map<String, dynamic> data, String prefix) {
      for (final key in ['name', 'phone', 'email', 'nic', 'address']) {
        controller('$prefix$key').text = data[key]?.toString() ?? '';
      }
      for (final key in ['id_front', 'id_back', 'license_front']) {
        if (data[key] is String) photos['$prefix$key'] = data[key] as String;
      }
    }

    fill(existing, '');
    busId = existing['bus_id'] as int?;
    assistant = existing['assistant'] != null;
    if (assistant) {
      fill(Map<String, dynamic>.from(existing['assistant'] as Map),
          'assistant_');
    }
  }

  @override
  void dispose() {
    for (final c in fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  Widget field(String key, String label,
          {bool phone = false,
          bool email = false,
          bool password = false,
          int min = 2,
          int max = 120}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: TextFormField(
            controller: controller(key),
            enabled: !saving,
            obscureText: password,
            maxLength: max,
            keyboardType: phone
                ? TextInputType.phone
                : email
                    ? TextInputType.emailAddress
                    : TextInputType.text,
            decoration: InputDecoration(labelText: label, counterText: ''),
            validator: (value) {
              final text = (value ?? '').trim();
              if (password &&
                  widget.existing != null &&
                  (value ?? '').isEmpty) {
                return null;
              }
              if (text.length < min) {
                return 'Enter $label (at least $min characters)';
              }
              if (phone && !RegExp(r'^\+?[0-9]{10,15}$').hasMatch(text)) {
                return 'Enter 10–15 digits, optionally starting with +';
              }
              if (email &&
                  !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(text)) {
                return 'Enter a valid email address';
              }
              if (password &&
                  (!RegExp('[A-Za-z]').hasMatch(text) ||
                      !RegExp('[0-9]').hasMatch(text) ||
                      utf8.encode(text).length > 72)) {
                return 'Use letters and numbers, up to 72 bytes';
              }
              return null;
            }),
      );
  Future<void> pick(String key) async {
    try {
      final image = await ImagePicker().pickImage(source: ImageSource.gallery);
      if (image == null) return;
      if (await image.length() > 5 * 1024 * 1024) {
        if (mounted) {
          setState(() => error = 'Each photo must be at most 5 MB.');
        }
        return;
      }
      final bytes = await image.readAsBytes();
      final png = bytes.length >= 8 &&
          bytes[0] == 137 &&
          bytes[1] == 80 &&
          bytes[2] == 78 &&
          bytes[3] == 71;
      final jpeg = bytes.length >= 3 &&
          bytes[0] == 255 &&
          bytes[1] == 216 &&
          bytes[2] == 255;
      if (!png && !jpeg) {
        if (mounted) setState(() => error = 'Choose a JPEG or PNG photo.');
        return;
      }
      if (mounted) {
        setState(() {
          photos[key] =
              'data:image/${png ? 'png' : 'jpeg'};base64,${base64Encode(bytes)}';
          error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => error = 'Unable to open photo library. Please retry.');
      }
    }
  }

  Widget photo(String key, String label) => FormField<String>(
      validator: (_) => photos.containsKey(key) ? null : 'Upload $label',
      builder: (state) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            OutlinedButton.icon(
                onPressed: saving
                    ? null
                    : () async {
                        await pick(key);
                        state.didChange(photos[key]);
                      },
                icon: Icon(photos.containsKey(key)
                    ? Icons.check_circle
                    : Icons.upload),
                label: Text(label)),
            if (photos.containsKey(key))
              Image.memory(base64Decode(photos[key]!.split(',').last),
                  height: 100,
                  errorBuilder: (_, __, ___) =>
                      const Text('Invalid image. Choose another photo.')),
            if (state.hasError)
              Text(state.errorText!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ])));
  List<Widget> identity(String prefix) => [
        field('${prefix}name', 'Full name'),
        field('${prefix}phone', 'Phone number', phone: true, max: 16),
        field('${prefix}email', 'Email address', email: true, max: 255),
        field('${prefix}nic', 'National ID number', min: 5, max: 30),
        field('${prefix}address', 'Residential address', min: 5, max: 500),
        photo('${prefix}id_front', 'ID front photo'),
        photo('${prefix}id_back', 'ID back photo'),
      ];
  Map<String, dynamic> details(String prefix) => {
        for (final key in ['name', 'phone', 'email', 'nic', 'address'])
          key: controller('$prefix$key').text.trim(),
        'id_front': photos['${prefix}id_front'],
        'id_back': photos['${prefix}id_back']
      };
  Future<void> save() async {
    if (!form.currentState!.validate()) return;
    setState(() {
      saving = true;
      error = null;
    });
    try {
      final api = ref.read(apiClientProvider).dio;
      final data = {
        ...details(''),
        if (widget.existing == null || controller('password').text.isNotEmpty)
          'password': controller('password').text,
        'license_front': photos['license_front'],
        'bus_id': busId,
        'assistant': assistant ? details('assistant_') : null
      };
      if (widget.existing == null) {
        await api.post('/admin/driver-registrations', data: data);
      } else {
        await api.put('/admin/driver-registrations/${widget.existing!['id']}',
            data: data);
      }
      if (mounted) Navigator.of(context).pop(true);
    } on DioException catch (e) {
      final detail =
          e.response?.data is Map ? e.response?.data['detail'] : null;
      if (mounted) {
        setState(() => error = detail is String
            ? detail
            : detail is List
                ? detail
                    .map((v) =>
                        '${(v['loc'] as List).skip(1).join('.')}: ${v['msg']}')
                    .join('\n')
                : 'Unable to save driver. Please retry.');
      }
    } catch (_) {
      if (mounted) {
        setState(() => error = 'Unable to save driver. Please retry.');
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(
          title: Text(widget.existing == null
              ? 'Create bus driver'
              : 'Edit bus driver')),
      body: Center(
          child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Form(
                  key: form,
                  child: SingleChildScrollView(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text('Driver details',
                                style:
                                    Theme.of(context).textTheme.headlineSmall),
                            const SizedBox(height: 16),
                            ...identity(''),
                            photo(
                                'license_front', 'Driving licence front photo'),
                            field(
                                'password',
                                widget.existing == null
                                    ? 'Login password'
                                    : 'New password (leave blank to keep current)',
                                password: true,
                                min: 8,
                                max: 72),
                            DropdownButtonFormField<int>(
                                initialValue: busId,
                                isExpanded: true,
                                decoration: const InputDecoration(
                                    labelText: 'Bus and route'),
                                items: [
                                  for (final bus in widget.buses)
                                    DropdownMenuItem(
                                        value: bus['id'] as int,
                                        child: Text(
                                            '${bus['plate_no']} — ${bus['route_name']}',
                                            overflow: TextOverflow.ellipsis))
                                ],
                                onChanged: saving
                                    ? null
                                    : (v) => setState(() => busId = v),
                                validator: (v) => v == null
                                    ? 'Select a bus and route'
                                    : null),
                            if (widget.buses.isEmpty)
                              const Text(
                                  'No buses available. Create a bus and route on the dashboard first.'),
                            SwitchListTile(
                                contentPadding: EdgeInsets.zero,
                                title: const Text('Driver has an assistant'),
                                value: assistant,
                                onChanged: saving
                                    ? null
                                    : (v) => setState(() => assistant = v)),
                            if (assistant) ...[
                              Text('Assistant details',
                                  style:
                                      Theme.of(context).textTheme.titleLarge),
                              const SizedBox(height: 16),
                              ...identity('assistant_')
                            ],
                            const Text(
                                'ID and driving licence photos: JPEG or PNG, up to 5 MB each. The driver signs in with the email and password entered above.'),
                            if (error != null)
                              Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 16),
                                  child: Text(error!,
                                      style: TextStyle(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .error))),
                            const SizedBox(height: 20),
                            FilledButton(
                                onPressed: saving || widget.buses.isEmpty
                                    ? null
                                    : save,
                                child: Text(saving
                                    ? 'Saving driver…'
                                    : widget.existing != null
                                        ? 'Save driver changes'
                                        : 'Create driver & assign bus')),
                          ]))))));
}
