class BusLocationModel {
  BusLocationModel({
    required this.busId,
    required this.lat,
    required this.lng,
    required this.serverTime,
    this.speed,
    this.heading,
  });

  factory BusLocationModel.fromJson(Map<String, dynamic> json) {
    return BusLocationModel(
      busId: json['bus_id'] as int? ?? 0,
      lat: (json['lat'] as num).toDouble(),
      lng: (json['lng'] as num).toDouble(),
      serverTime: DateTime.tryParse(json['server_time'] ?? '') ?? DateTime.now(),
      speed: json['speed'] as num?,
      heading: json['heading'] as num?,
    );
  }

  final int busId;
  final double lat;
  final double lng;
  final DateTime serverTime;
  final num? speed;
  final num? heading;
}
