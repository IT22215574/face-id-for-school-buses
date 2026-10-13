import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../dashboard/dashboard_screen.dart';
import 'transport_state.dart';

class SelectChildScreen extends ConsumerWidget {
  const SelectChildScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(transportStudentsProvider);
    return Scaffold(
        backgroundColor: busBlue,
        appBar: AppBar(),
        body: SafeArea(
            child: Center(
                child: SingleChildScrollView(
                    padding: const EdgeInsets.all(32),
                    child: Column(children: [
                      const Text('Select child',
                          style: TextStyle(
                              fontSize: 30,
                              color: Colors.white,
                              fontWeight: FontWeight.bold)),
                      const SizedBox(height: 36),
                      Wrap(
                          spacing: 30,
                          runSpacing: 24,
                          alignment: WrapAlignment.center,
                          children: [
                            for (var i = 0; i < students.length; i++)
                              SizedBox(
                                  width: 130,
                                  child: Column(children: [
                                    IconButton(
                                        tooltip: students[i].name,
                                        onPressed: () {
                                          ref
                                              .read(selectedChildProvider
                                                  .notifier)
                                              .state = i;
                                          Navigator.of(context).pushReplacement(
                                              MaterialPageRoute<void>(
                                                  settings: const RouteSettings(
                                                      name: 'transport-home'),
                                                  builder: (_) =>
                                                      const DashboardScreen()));
                                        },
                                        icon: DesignAsset(
                                            i.isEven
                                                ? 'f0a5b.svg'
                                                : 'a17df.svg',
                                            width: 110,
                                            height: 110)),
                                    Text(students[i].name,
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                            color: Colors.white)),
                                  ]))
                          ]),
                      const SizedBox(height: 56),
                      const Text('Add child',
                          style: TextStyle(
                              fontSize: 30,
                              color: Colors.white,
                              fontWeight: FontWeight.bold)),
                      const SizedBox(height: 20),
                      IconButton(
                          tooltip: 'Add child',
                          onPressed: () =>
                              openScreen(context, const AddStudentScreen()),
                          icon: const SizedBox(
                              width: 110,
                              height: 110,
                              child:
                                  Stack(alignment: Alignment.center, children: [
                                DesignAsset('a2257.svg',
                                    width: 110, height: 110),
                                DesignAsset('00d84.svg', width: 68, height: 70)
                              ]))),
                    ])))));
  }
}

class AddStudentScreen extends ConsumerStatefulWidget {
  const AddStudentScreen({super.key, this.driver = false});
  final bool driver;
  @override
  ConsumerState<AddStudentScreen> createState() => _AddStudentScreenState();
}

class _AddStudentScreenState extends ConsumerState<AddStudentScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _pickup = TextEditingController();
  final _notes = TextEditingController();
  final _parent = TextEditingController();
  final _phone = TextEditingController();
  String _school = 'Royal College, Colombo 07';
  String _grade = 'Grade 6 · Class A';
  String _relationship = 'Mother / guardian';
  @override
  void dispose() {
    for (final c in [_name, _pickup, _notes, _parent, _phone]) {
      c.dispose();
    }
    super.dispose();
  }

  Widget field(String label, TextEditingController controller,
          {bool required = true, TextInputType? keyboard}) =>
      Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: TextFormField(
              controller: controller,
              keyboardType: keyboard,
              decoration: InputDecoration(labelText: label),
              validator: (value) =>
                  required && (value == null || value.trim().isEmpty)
                      ? 'Please enter $label'
                      : null));
  Widget choice(String label, String value, List<String> choices,
          ValueChanged<String> change) =>
      Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: DropdownButtonFormField<String>(
              initialValue: value,
              isExpanded: true,
              decoration: InputDecoration(labelText: label),
              items: choices
                  .map((v) => DropdownMenuItem(
                      value: v,
                      child: Text(v, style: const TextStyle(fontSize: 14))))
                  .toList(),
              onChanged: (v) {
                if (v != null) setState(() => change(v));
              }));
  void save() {
    if (!_formKey.currentState!.validate()) return;
    final existing = ref.read(transportStudentsProvider);
    ref.read(transportStudentsProvider.notifier).state = [
      ...existing,
      TransportStudent(
          name: _name.text.trim(),
          school: _school,
          grade: _grade,
          pickup: _pickup.text.trim(),
          parent:
              _parent.text.trim().isEmpty ? 'Guardian' : _parent.text.trim(),
          phone: _phone.text.trim(),
          notes: _notes.text.trim().isEmpty
              ? 'No additional care requirements'
              : _notes.text.trim(),
          present: false)
    ];
    if (!widget.driver) {
      ref.read(selectedChildProvider.notifier).state = existing.length;
    }
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Saved in this UI preview session')));
  }

  @override
  Widget build(BuildContext context) => BusScaffold(
      title: widget.driver ? 'Add Student' : 'Add your child',
      padding: const EdgeInsets.all(32),
      child: Form(
          key: _formKey,
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            field('Student’s full name', _name),
            choice(
                'School',
                _school,
                ['Royal College, Colombo 07', 'Visakha Vidyalaya, Colombo 05'],
                (v) => _school = v),
            choice(
                'Grade / class',
                _grade,
                ['Grade 6 · Class A', 'Grade 3 · Class B', 'Grade 7 · Class A'],
                (v) => _grade = v),
            if (!widget.driver)
              choice(
                  'Relationship to student',
                  _relationship,
                  ['Mother / guardian', 'Father / guardian'],
                  (v) => _relationship = v),
            field('Pickup area', _pickup),
            if (widget.driver) ...[
              field('Parent’s name', _parent),
              field('Mobile number', _phone, keyboard: TextInputType.phone)
            ] else
              const Padding(
                  padding: EdgeInsets.only(bottom: 20),
                  child:
                      DetailField('SELECT DRIVER', 'D-024 · Sunil Fernando')),
            field('Additional care notes (optional)', _notes, required: false),
            const Text('Shared only with authorised school transport staff.',
                style: TextStyle(color: busMuted, fontSize: 11)),
            const SizedBox(height: 20),
            SizedBox(
                width: double.infinity,
                child: FilledButton(
                    onPressed: save,
                    child: Text(widget.driver
                        ? 'Save student'
                        : 'Save child & continue'))),
          ])));
}

class StudentListScreen extends ConsumerStatefulWidget {
  const StudentListScreen({super.key});
  @override
  ConsumerState<StudentListScreen> createState() => _StudentListScreenState();
}

class _StudentListScreenState extends ConsumerState<StudentListScreen> {
  String query = '';
  @override
  Widget build(BuildContext context) {
    final students = ref
        .watch(transportStudentsProvider)
        .where((s) => s.name.toLowerCase().contains(query.toLowerCase()))
        .toList();
    return BusScaffold(
        title: 'Student Details',
        child: Column(children: [
          TextField(
              decoration: const InputDecoration(
                  labelText: 'Search students', prefixIcon: Icon(Icons.search)),
              onChanged: (v) => setState(() => query = v)),
          const SizedBox(height: 24),
          if (students.isEmpty) const Text('No students found.'),
          for (final student in students)
            Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: BusCard(
                    child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const CircleAvatar(
                            backgroundColor: busBlue,
                            child: Icon(Icons.person, color: Colors.white)),
                        title: Text(student.name),
                        subtitle: Text(student.grade),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => openScreen(
                            context, StudentProfileScreen(student: student))))),
        ]));
  }
}

class StudentProfileScreen extends StatelessWidget {
  const StudentProfileScreen({super.key, required this.student});
  final TransportStudent student;
  @override
  Widget build(BuildContext context) => BusScaffold(
      title: student.name,
      padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 40),
      child: BusCard(
          color: const Color(0xFFDFE2E7),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 56),
          child: BusCard(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(student.name,
                    style: const TextStyle(
                        color: Color(0xFF173B65),
                        fontWeight: FontWeight.bold,
                        fontSize: 19)),
                const SizedBox(height: 12),
                Text(student.parent,
                    style: const TextStyle(
                        color: Color(0xFF173B65), fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Text('${student.grade} · ${student.school}',
                    style: const TextStyle(color: busMuted, fontSize: 13)),
                const SizedBox(height: 24),
                DetailField('MOBILE NUMBER',
                    student.phone.isEmpty ? 'Not provided' : student.phone),
                DetailField('ADDRESS', student.pickup),
                DetailField('SCHOOL', student.school),
                DetailField('ADDITIONAL CARE NOTES', student.notes),
              ]))));
}
