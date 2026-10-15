import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../dashboard/dashboard_screen.dart';
import 'transport_state.dart';
import '../auth/sign_out.dart';

class SelectChildScreen extends ConsumerWidget {
  const SelectChildScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loading = ref.watch(transportLoadProvider);
    final students = ref.watch(transportStudentsProvider);
    if (loading.isLoading || loading.hasError || students.isEmpty) {
      return Scaffold(
          appBar: AppBar(title: const Text('Your children')),
          body: Center(
              child: loading.isLoading
                  ? const CircularProgressIndicator()
                  : Column(mainAxisSize: MainAxisSize.min, children: [
                      Text(loading.hasError
                          ? 'Could not load assigned children.'
                          : 'No children assigned. Ask your school to link your child and bus.'),
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
                    ])))));
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
