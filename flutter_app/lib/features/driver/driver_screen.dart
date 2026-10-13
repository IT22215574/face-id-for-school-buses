import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../auth/sign_out.dart';
import '../map/live_map_screen.dart';
import '../transport/student_screens.dart';
import '../transport/transport_state.dart';

class DriverScreen extends ConsumerWidget {
  const DriverScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(transportStudentsProvider);
    final present = students.where((s) => s.present).length;
    return Scaffold(
        body: SafeArea(
            top: false,
            child: Align(
                alignment: Alignment.topCenter,
                child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 600),
                    child: SingleChildScrollView(
                        child: Column(children: [
                      HomeHeader(
                          driver: true,
                          action: IconButton.filled(
                              tooltip: 'SOS',
                              style: IconButton.styleFrom(
                                  backgroundColor: const Color(0xFFF62727),
                                  minimumSize: const Size(48, 48)),
                              onPressed: () =>
                                  openScreen(context, const SosScreen()),
                              icon: const DesignAsset('41648.svg',
                                  width: 29, height: 29)),
                          details: Text(
                              'Sunil Fernando\nWP NC-1234\n$present students in bus\nDriver ID: D-024',
                              style: const TextStyle(
                                  fontSize: 15, color: Colors.black))),
                      Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 23),
                          child: Column(children: [
                            Row(children: [
                              const Expanded(
                                  child: Text('Live bus location',
                                      style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.bold))),
                              TextButton(
                                  onPressed: () => openScreen(
                                      context, const LiveMapScreen()),
                                  child: const Text('View'))
                            ]),
                            BusCard(
                                child: ListTile(
                              leading: const Icon(Icons.map, color: busBlue),
                              title: const Text('Track your bus on the map'),
                              subtitle: const Text(
                                  'Share GPS from your phone during your trip'),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () =>
                                  openScreen(context, const LiveMapScreen()),
                            )),
                            const SizedBox(height: 24),
                            SizedBox(
                                width: double.infinity,
                                child: FilledButton(
                                    style: FilledButton.styleFrom(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 24, vertical: 24)),
                                    onPressed: () => openScreen(
                                        context, const AttendanceScreen()),
                                    child: Row(children: [
                                      const Expanded(
                                          child: Text(
                                              'Today’s Student Attendance',
                                              style: TextStyle(
                                                  fontWeight:
                                                      FontWeight.bold))),
                                      Text('$present/${students.length}')
                                    ]))),
                            const SizedBox(height: 24),
                            Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  DriverAction(
                                      label: 'Students',
                                      asset: '642ec.svg',
                                      onTap: () => openScreen(
                                          context, const StudentListScreen())),
                                  DriverAction(
                                      label: 'Add student',
                                      asset: 'fde92.svg',
                                      composite: true,
                                      onTap: () => openScreen(
                                          context,
                                          const AddStudentScreen(
                                              driver: true))),
                                  DriverAction(
                                      label: 'Attendance',
                                      onTap: () => openScreen(
                                          context, const AttendanceScreen())),
                                ]),
                            const SizedBox(height: 32),
                          ])),
                    ]))))),
        bottomNavigationBar:
            BusBottomBar(onHome: () {}, onSwitch: () => signOut(context, ref)));
  }
}

class DriverAction extends StatelessWidget {
  const DriverAction(
      {super.key,
      required this.label,
      required this.onTap,
      this.asset,
      this.composite = false});
  final String label;
  final VoidCallback onTap;
  final String? asset;
  final bool composite;
  @override
  Widget build(BuildContext context) => Expanded(
      child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 5),
          child: Column(children: [
            Semantics(
                label: label,
                button: true,
                child: InkWell(
                    onTap: onTap,
                    borderRadius: BorderRadius.circular(20),
                    child: composite
                        ? const DesignAsset('fde92.svg',
                            width: 107, height: 100)
                        : BusCard(
                            padding: const EdgeInsets.symmetric(
                                vertical: 13, horizontal: 8),
                            child: SizedBox(
                                height: 65,
                                width: 83,
                                child: Stack(
                                    alignment: Alignment.center,
                                    children: [
                                      const DesignAsset('09a03.svg',
                                          width: 65, height: 65),
                                      if (asset != null)
                                        DesignAsset(asset!,
                                            width: 37, height: 37)
                                    ]))))),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(fontSize: 11)),
          ])));
}

class AttendanceScreen extends ConsumerWidget {
  const AttendanceScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(transportStudentsProvider);
    final present = students.where((s) => s.present).length;
    return BusScaffold(
        title: 'Today’s Attendance',
        child: Column(children: [
          Row(children: [
            Expanded(child: _CountCard('Present', present)),
            const SizedBox(width: 36),
            Expanded(child: _CountCard('Absent', students.length - present))
          ]),
          const SizedBox(height: 34),
          const Text('Sample attendance · Morning / Evening',
              style: TextStyle(fontSize: 12, color: busMuted)),
          const SizedBox(height: 16),
          Table(
              columnWidths: const {0: FlexColumnWidth(1.5)},
              border: TableBorder.all(color: Colors.white, width: 2),
              children: [
                TableRow(
                    children: [
                  'Name',
                  'AM\nPickup',
                  'AM\nDrop off',
                  'PM\nPickup',
                  'PM\nDrop off'
                ]
                        .map((label) => Padding(
                            padding: const EdgeInsets.symmetric(
                                vertical: 12, horizontal: 3),
                            child: Text(label,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold))))
                        .toList()),
                for (final student in students)
                  TableRow(
                      decoration: const BoxDecoration(color: Color(0xFFDFE2E7)),
                      children: [
                        student.name,
                        student.present ? '07:30' : 'Absent',
                        student.present ? '08:15' : '—',
                        '—',
                        '—'
                      ]
                          .map((value) => Padding(
                              padding: const EdgeInsets.symmetric(
                                  vertical: 16, horizontal: 4),
                              child: Text(value,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 11))))
                          .toList()),
              ]),
        ]));
  }
}

class _CountCard extends StatelessWidget {
  const _CountCard(this.label, this.count);
  final String label;
  final int count;
  @override
  Widget build(BuildContext context) => BusCard(
      child: SizedBox(
          height: 104,
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Text('$count',
                style: const TextStyle(
                    fontSize: 32, color: busBlue, fontWeight: FontWeight.bold))
          ])));
}

class SosScreen extends StatelessWidget {
  const SosScreen({super.key});
  @override
  Widget build(BuildContext context) => BusScaffold(
      title: 'SOS',
      child: Column(children: [
        const Text('Select the type of assistance',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 32),
        for (final label in [
          'Medical assistance',
          'Vehicle breakdown',
          'Contact school'
        ])
          Padding(
              padding: const EdgeInsets.only(bottom: 18),
              child: SizedBox(
                  width: 200,
                  height: 145,
                  child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () => showDialog<void>(
                          context: context,
                          builder: (context) => AlertDialog(
                                  title: Text(label),
                                  content: const Text(
                                      'This is a UI preview. Emergency calls and alerts are not connected.'),
                                  actions: [
                                    TextButton(
                                        onPressed: () => Navigator.pop(context),
                                        child: const Text('Close'))
                                  ])),
                      child: BusCard(
                          color: const Color(0xFFD9D9D9),
                          child: Align(
                              alignment: Alignment.topCenter,
                              child: Text(label,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold))))))),
      ]));
}
