import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

class TransportStudent {
  const TransportStudent(
      {required this.name,
      this.id,
      this.busId,
      this.school = '',
      this.grade = '',
      this.parent = '',
      this.phone = '',
      this.fatherPhone = '',
      this.motherPhone = '',
      this.pickup = '',
      this.notes = '',
      this.present = false,
      this.driverName = '',
      this.driverPhone = '',
      this.plate = ''});
  final int? id, busId;
  final String name, school, grade, parent, phone, pickup, notes;
  final String driverName, driverPhone, plate;
  final String fatherPhone, motherPhone;
  final bool present;
  factory TransportStudent.fromJson(Map<String, dynamic> data) =>
      TransportStudent(
          present: data['present'] == true,
          id: data['id'] as int,
          busId: data['bus_id'] as int?,
          name: data['name'] as String,
          school: data['school']['name'] as String,
          grade: data['grade'] as String,
          parent: data['parent'] as String,
          phone: data['phone'] as String,
          fatherPhone: data['father_phone'] as String? ?? '',
          motherPhone: data['mother_phone'] as String? ?? '',
          driverName: data['driver_name'] as String? ?? 'No driver assigned',
          driverPhone: data['driver_phone'] as String? ?? '',
          plate: data['plate_no'] as String? ?? 'No bus assigned');
}

final transportLoadProvider = FutureProvider.autoDispose<void>((ref) async {
  ref.watch(authStateProvider);
  final response = await ref.read(apiClientProvider).dio.get('/me/transport');
  ref.read(transportStudentsProvider.notifier).state = (response.data as List)
      .map((item) =>
          TransportStudent.fromJson(Map<String, dynamic>.from(item as Map)))
      .toList();
});
final transportStudentsProvider =
    StateProvider<List<TransportStudent>>((ref) => []);
final selectedChildProvider = StateProvider<int>((ref) => 0);
