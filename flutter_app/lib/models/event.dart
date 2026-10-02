class BusEvent {
  BusEvent({
    required this.id,
    required this.studentId,
    required this.busId,
    required this.eventType,
    required this.eventTime,
    required this.lat,
    required this.lng,
    required this.source,
  });

  factory BusEvent.fromJson(Map<String, dynamic> json) {
    return BusEvent(
      id: json['id'] as int,
      studentId: json['student_id'] as int,
      busId: json['bus_id'] as int,
      eventType: json['event_type'] as String,
      eventTime: DateTime.tryParse(json['event_time'] ?? '') ?? DateTime.now(),
      lat: (json['lat'] as num).toDouble(),
      lng: (json['lng'] as num).toDouble(),
      source: json['source'] as String? ?? 'DEVICE',
    );
  }

  final int id;
  final int studentId;
  final int busId;
  final String eventType;
  final DateTime eventTime;
  final double lat;
  final double lng;
  final String source;
}
