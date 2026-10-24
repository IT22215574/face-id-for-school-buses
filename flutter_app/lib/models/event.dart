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
    this.receivedAt,
    this.gpsStatus,
    this.isDelayed = false,
  });

  factory BusEvent.fromJson(Map<String, dynamic> json) {
    return BusEvent(
      id: json['id'] as int,
      studentId: json['student_id'] as int,
      busId: json['bus_id'] as int,
      eventType: json['event_type'] as String,
      eventTime: DateTime.parse(json['event_time'] as String),
      lat: (json['lat'] as num?)?.toDouble(),
      lng: (json['lng'] as num?)?.toDouble(),
      source: json['source'] as String? ?? 'DEVICE',
      receivedAt: json['received_at'] == null
          ? null
          : DateTime.parse(json['received_at'] as String),
      gpsStatus: json['gps_status'] as String?,
      isDelayed: json['is_delayed'] == true,
    );
  }

  final int id;
  final int studentId;
  final int busId;
  final String eventType;
  final DateTime eventTime;
  final double? lat;
  final double? lng;
  final String source;
  final DateTime? receivedAt;
  final String? gpsStatus;
  final bool isDelayed;
}
