class Student {
  Student({
    required this.id,
    required this.name,
    required this.grade,
    required this.schoolId,
  });

  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      id: json['id'] as int,
      name: json['name'] as String,
      grade: json['grade'] as String,
      schoolId: json['school_id'] as String,
    );
  }

  final int id;
  final String name;
  final String grade;
  final String schoolId;
}
