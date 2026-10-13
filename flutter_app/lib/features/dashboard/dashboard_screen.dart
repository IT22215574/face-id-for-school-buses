import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../map/map_screen.dart';
import '../notifications/notifications_screen.dart';
import '../transport/student_screens.dart';
import '../transport/transport_state.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(transportStudentsProvider);
    final index =
        ref.watch(selectedChildProvider).clamp(0, students.length - 1);
    final student = students[index];
    return Scaffold(
      body: SafeArea(
          top: false,
          child: Center(
              child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 600),
                  child: SingleChildScrollView(
                      child: Column(children: [
                    SizedBox(
                        height: 278,
                        child: Stack(children: [
                          Container(
                              height: 210,
                              decoration: const BoxDecoration(
                                  color: busBlue,
                                  borderRadius: BorderRadius.vertical(
                                      bottom: Radius.circular(20)),
                                  boxShadow: [
                                    BoxShadow(
                                        color: Color(0x33000000),
                                        blurRadius: 4,
                                        offset: Offset(0, 4))
                                  ])),
                          Positioned(
                              top: 28 + MediaQuery.paddingOf(context).top,
                              right: 38,
                              child: IconButton(
                                  tooltip: 'Notifications',
                                  onPressed: () => openScreen(
                                      context, const NotificationsScreen()),
                                  icon: const DesignAsset('29a4b.svg',
                                      width: 27, height: 27))),
                          Positioned(
                              top: 105,
                              left: 42,
                              right: 42,
                              child: BusCard(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 25, vertical: 24),
                                  child: SizedBox(
                                      height: 108,
                                      child: Row(children: [
                                        const ProfileAvatar(),
                                        const SizedBox(width: 28),
                                        Expanded(
                                            child: Column(
                                                mainAxisAlignment:
                                                    MainAxisAlignment.center,
                                                crossAxisAlignment:
                                                    CrossAxisAlignment.start,
                                                children: [
                                              Text(student.name,
                                                  style: const TextStyle(
                                                      color: Colors.black,
                                                      fontSize: 15)),
                                              Text(student.grade,
                                                  style: const TextStyle(
                                                      color: Colors.black,
                                                      fontSize: 15)),
                                              InkWell(
                                                  onTap: () => openScreen(
                                                      context,
                                                      const SelectChildScreen()),
                                                  child: const Padding(
                                                      padding:
                                                          EdgeInsets.symmetric(
                                                              vertical: 8),
                                                      child: Text(
                                                          'Switch child  ▾',
                                                          style: TextStyle(
                                                              fontSize: 12,
                                                              color:
                                                                  busMuted)))),
                                            ])),
                                      ])))),
                        ])),
                    Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 26),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Today’s Journey',
                                  style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold)),
                              const SizedBox(height: 16),
                              const Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Expanded(child: JourneyCard(morning: true)),
                                    SizedBox(width: 16),
                                    Expanded(child: JourneyCard(morning: false))
                                  ]),
                              const SizedBox(height: 18),
                              Row(children: [
                                const Expanded(
                                    child: Text('School Bus Detector',
                                        style: TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.bold))),
                                TextButton(
                                    onPressed: () =>
                                        openScreen(context, const MapScreen()),
                                    child: const Text('View map'))
                              ]),
                              BusMapPreview(
                                  onTap: () =>
                                      openScreen(context, const MapScreen())),
                              const SizedBox(height: 20),
                              Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceEvenly,
                                  children: [
                                    IconButton(
                                        tooltip: 'Driver Profile',
                                        onPressed: () => showTransportProfile(
                                            context,
                                            school: false),
                                        icon: const DesignAsset('70e73.svg',
                                            width: 82, height: 81)),
                                    IconButton(
                                        tooltip: 'School Profile',
                                        onPressed: () => showTransportProfile(
                                            context,
                                            school: true),
                                        icon: const DesignAsset('6d26b.svg',
                                            width: 82, height: 81)),
                                  ]),
                              const SizedBox(height: 24),
                            ])),
                  ]))))),
      bottomNavigationBar: BusBottomBar(
          onHome: () {},
          onSwitch: () =>
              Navigator.of(context).popUntil((route) => route.isFirst)),
    );
  }
}

class JourneyCard extends StatelessWidget {
  const JourneyCard({super.key, required this.morning});
  final bool morning;
  @override
  Widget build(BuildContext context) => BusCard(
      radius: 16,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
              width: 8,
              height: 8,
              decoration:
                  const BoxDecoration(color: busBlue, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Expanded(
              child: Text(morning ? 'Morning Journey' : 'Evening Journey',
                  style: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.bold)))
        ]),
        const SizedBox(height: 12),
        const Text('Pickup Time',
            style: TextStyle(color: busMuted, fontSize: 14)),
        const SizedBox(height: 4),
        Text(morning ? '07:30 AM' : '03:00 PM',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        const Text('Dropoff Time',
            style: TextStyle(color: busMuted, fontSize: 14)),
        const SizedBox(height: 4),
        Text(morning ? '08:15 AM' : '03:45 PM',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      ]));
}

void showTransportProfile(BuildContext context, {required bool school}) {
  showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(12))),
      builder: (context) => SafeArea(
          child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      school
                          ? const DesignAsset('05112.svg',
                              width: 38, height: 38)
                          : const DesignAsset('28284.svg',
                              width: 36, height: 36),
                      const SizedBox(width: 12),
                      Expanded(
                          child: Text(
                              school ? 'School Profile' : 'Driver Profile',
                              style: const TextStyle(
                                  fontSize: 18, fontWeight: FontWeight.bold))),
                      IconButton(
                          tooltip: 'Close',
                          onPressed: () => Navigator.pop(context),
                          icon: const DesignAsset('97924.svg',
                              width: 16, height: 16))
                    ]),
                    const SizedBox(height: 24),
                    DetailField(
                        school ? 'SCHOOL NAME' : 'DRIVER’S NAME',
                        school
                            ? 'Royal College, Colombo 07'
                            : 'Sunil Fernando'),
                    DetailField(
                        school ? 'SCHOOL’S ADDRESS' : 'CONTACT DETAILS',
                        school
                            ? 'Rajakeeya Mawatha, Colombo 07'
                            : '077 555 0123'),
                    DetailField(
                        school ? 'CONTACT DETAILS' : 'VEHICLE NUMBER',
                        school
                            ? '011 269 5256 · office@royalcollege.lk'
                            : 'WP NC-1234'),
                    const SizedBox(height: 32),
                  ]))));
}
