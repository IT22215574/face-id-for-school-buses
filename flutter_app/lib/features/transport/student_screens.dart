import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../dashboard/dashboard_screen.dart';
import 'transport_state.dart';
import '../auth/sign_out.dart';

class SelectChildScreen extends ConsumerWidget {
  const SelectChildScreen({super.key, this.switching = false});
  final bool switching;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loading = ref.watch(transportLoadProvider);
    final students = ref.watch(transportStudentsProvider);
    if (loading.isLoading || loading.hasError || students.isEmpty) {
      return Scaffold(
          appBar: AppBar(title: const Text('Your children')),
          bottomNavigationBar:
              BusBottomBar(onSwitch: () => signOut(context, ref)),
          body: Center(
              child: loading.isLoading
                  ? const CircularProgressIndicator()
                  : Column(mainAxisSize: MainAxisSize.min, children: [
                      Text(loading.hasError
                          ? 'Could not load assigned children.'
                          : 'No children added yet. Ask your driver to add your child using your registered email.'),
                      TextButton(
                          onPressed: () =>
                              ref.invalidate(transportLoadProvider),
                          child: const Text('Retry')),
                      TextButton(
                          onPressed: () => signOut(context, ref),
                          child: const Text('Sign out')),
                    ])));
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Your children'),
        flexibleSpace: const DecoratedBox(
            decoration: BoxDecoration(gradient: busGradient)),
      ),
      bottomNavigationBar: BusBottomBar(onSwitch: () => signOut(context, ref)),
      body: SafeArea(
          child: Center(
              child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: ListView(padding: const EdgeInsets.all(24), children: [
          const Text('Who are we following today?',
              style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.7)),
          const SizedBox(height: 10),
          const Text(
              'Choose a child to see their journey, bus location and school details.',
              style: TextStyle(color: busMuted, height: 1.5)),
          const SizedBox(height: 28),
          for (var i = 0; i < students.length; i++)
            Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Tooltip(
                  message: students[i].name,
                  child: Material(
                    color: Colors.white,
                    clipBehavior: Clip.antiAlias,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(24),
                        side: const BorderSide(color: Color(0xFFE1E8F2))),
                    child: InkWell(
                        onTap: () {
                          ref.read(selectedChildProvider.notifier).state = i;
                          if (switching) {
                            Navigator.of(context).pop();
                          } else {
                            Navigator.of(context).pushReplacement(
                                MaterialPageRoute<void>(
                                    settings: const RouteSettings(
                                        name: 'transport-home'),
                                    builder: (_) => const DashboardScreen()));
                          }
                        },
                        child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Row(children: [
                              Container(
                                  width: 60,
                                  height: 60,
                                  decoration: BoxDecoration(
                                      gradient: busSoftGradient,
                                      borderRadius: BorderRadius.circular(20)),
                                  child: const Icon(Icons.face_rounded,
                                      color: busBlue, size: 32)),
                              const SizedBox(width: 16),
                              Expanded(
                                  child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                    Text(students[i].name,
                                        style: const TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.w700)),
                                    if (students[i].grade.isNotEmpty) ...[
                                      const SizedBox(height: 4),
                                      Text(students[i].grade,
                                          style:
                                              const TextStyle(color: busMuted)),
                                    ],
                                    if (students[i].school.isNotEmpty) ...[
                                      const SizedBox(height: 4),
                                      Text(students[i].school,
                                          style: const TextStyle(
                                              fontSize: 12, color: busMuted)),
                                    ],
                                  ])),
                              const SizedBox(width: 8),
                              const Icon(Icons.arrow_forward_rounded,
                                  color: busBlue, size: 22),
                            ]))),
                  ),
                )),
        ]),
      ))),
    );
  }
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
                            backgroundColor: Color(0xFF132D65),
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
                DetailField(
                    'FATHER’S MOBILE NUMBER',
                    student.fatherPhone.isEmpty
                        ? 'Not provided'
                        : student.fatherPhone),
                DetailField(
                    'MOTHER’S MOBILE NUMBER',
                    student.motherPhone.isEmpty
                        ? 'Not provided'
                        : student.motherPhone),
                DetailField('ADDRESS', student.pickup),
                DetailField('SCHOOL', student.school),
                DetailField('ADDITIONAL CARE NOTES', student.notes),
              ]))));
}
