import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/bus_ui.dart';
import '../auth/sign_out.dart';
import '../map/map_screen.dart';
import '../notifications/notifications_screen.dart';
import '../transport/student_screens.dart';
import '../transport/transport_state.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});
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
    final index =
        ref.watch(selectedChildProvider).clamp(0, students.length - 1);
    final student = students[index];
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
                        action: IconButton(
                            tooltip: 'Notifications',
                            onPressed: () => openScreen(
                                context, const NotificationsScreen()),
                            icon: const DesignAsset('29a4b.svg',
                                width: 27, height: 27)),
                        details: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(student.name,
                                  style: const TextStyle(
                                      color: Colors.black, fontSize: 15)),
                              Text(student.grade,
                                  style: const TextStyle(
                                      color: Colors.black, fontSize: 15)),
                              InkWell(
                                  onTap: () => openScreen(
                                      context, const SelectChildScreen()),
                                  child: const Padding(
                                      padding:
                                          EdgeInsets.symmetric(vertical: 8),
                                      child: Text('Switch child',
                                          style: TextStyle(
                                              fontSize: 12, color: busMuted)))),
                            ])),
                    Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 26),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Today’s Journey',
                                  style: TextStyle(
                                      fontSize: 18,
                                      height: 1.2,
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
                                    child: Text('Live bus tracking',
                                        style: TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.bold))),
                                TextButton(
                                    style: TextButton.styleFrom(
                                        backgroundColor: busBlue,
                                        foregroundColor: Colors.white,
                                        minimumSize: const Size(105, 48),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 12),
                                        tapTargetSize:
                                            MaterialTapTargetSize.shrinkWrap,
                                        shape: const StadiumBorder()),
                                    onPressed: () =>
                                        openScreen(context, const MapScreen()),
                                    child: const Text('View map',
                                        style: TextStyle(fontSize: 12)))
                              ]),
                              BusCard(
                                  child: ListTile(
                                leading: const Icon(Icons.location_on,
                                    color: busBlue),
                                title: Text(student.plate),
                                subtitle: Text(
                                    '${student.school} · Open live tracking'),
                                onTap: () =>
                                    openScreen(context, const MapScreen()),
                              )),
                              const SizedBox(height: 20),
                              Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceEvenly,
                                  children: [
                                    IconButton(
                                        tooltip: 'Driver Profile',
                                        onPressed: () => showTransportProfile(
                                            context,
                                            school: false,
                                            student: student),
                                        icon: const DesignAsset('70e73.svg',
                                            width: 82, height: 81)),
                                    IconButton(
                                        tooltip: 'School Profile',
                                        onPressed: () => showTransportProfile(
                                            context,
                                            school: true,
                                            student: student),
                                        icon: const DesignAsset('6d26b.svg',
                                            width: 82, height: 81)),
                                  ]),
                              const SizedBox(height: 24),
                            ])),
                  ]))))),
      bottomNavigationBar:
          BusBottomBar(onHome: () {}, onSwitch: () => signOut(context, ref)),
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

void showTransportProfile(BuildContext context,
    {required bool school, required TransportStudent student}) {
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
                          ? const DesignAsset('39792.svg',
                              width: 38, height: 38)
                          : const SizedBox(
                              width: 45,
                              height: 44,
                              child:
                                  Stack(alignment: Alignment.center, children: [
                                DesignAsset('9e7a6.svg', width: 45, height: 44),
                                DesignAsset('28284.svg', width: 36, height: 36)
                              ])),
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
                    DetailField(school ? 'SCHOOL NAME' : 'DRIVER’S NAME',
                        school ? student.school : student.driverName),
                    DetailField(school ? 'SCHOOL’S ADDRESS' : 'CONTACT DETAILS',
                        school ? 'Kurunegala' : student.driverPhone),
                    DetailField(school ? 'CONTACT DETAILS' : 'VEHICLE NUMBER',
                        school ? 'Contact your school office' : student.plate),
                    const SizedBox(height: 32),
                  ]))));
}
