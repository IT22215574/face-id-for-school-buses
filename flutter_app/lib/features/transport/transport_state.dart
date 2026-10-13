import 'package:flutter_riverpod/flutter_riverpod.dart';

class TransportStudent {
  const TransportStudent(
      {required this.name,
      this.school = 'Royal College, Colombo 07',
      this.grade = 'Grade 6 · Class A',
      this.parent = 'Nimali Perera',
      this.phone = '077 123 4567',
      this.pickup = 'Pannipitiya · High Level Road',
      this.notes = 'No additional care requirements',
      this.present = true});
  final String name, school, grade, parent, phone, pickup, notes;
  final bool present;
}

// Local UI preview data, pending transport API integration.
final transportStudentsProvider =
    StateProvider<List<TransportStudent>>((ref) => const [
          TransportStudent(name: 'Kavindu Perera'),
          TransportStudent(
              name: 'Amaya Perera', grade: 'Grade 3 · Class B', present: false)
        ]);
final selectedChildProvider = StateProvider<int>((ref) => 0);
