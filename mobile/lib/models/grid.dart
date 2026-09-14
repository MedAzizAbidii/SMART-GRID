/// Mirrors one entry of GET /api/grid/all's "buses" array — the same 14
/// simulated buses the web dashboard's GridNetwork.jsx renders. Every field
/// here is real telemetry; nothing is fabricated at a different scale.
class GridBus {
  final double timestamp;
  final int busId;
  final double voltage;
  final double current;
  final double frequency;
  final double consumption;
  final String consumerType;
  final String attackType;

  GridBus({
    required this.timestamp,
    required this.busId,
    required this.voltage,
    required this.current,
    required this.frequency,
    required this.consumption,
    required this.consumerType,
    required this.attackType,
  });

  bool get isAttacked => attackType != 'normal';
  String get meterId => 'SM_${busId.toString().padLeft(2, '0')}';

  factory GridBus.fromJson(Map<String, dynamic> json) => GridBus(
        timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0,
        busId: (json['bus_id'] as num?)?.toInt() ?? 0,
        voltage: (json['voltage'] as num?)?.toDouble() ?? 0,
        current: (json['current'] as num?)?.toDouble() ?? 0,
        frequency: (json['frequency'] as num?)?.toDouble() ?? 0,
        consumption: (json['consumption'] as num?)?.toDouble() ?? 0,
        consumerType: json['consumer_type'] as String? ?? 'mixed',
        attackType: json['attack_type'] as String? ?? 'normal',
      );
}

class GridSnapshot {
  final double timestamp;
  final List<GridBus> buses;

  GridSnapshot({required this.timestamp, required this.buses});

  factory GridSnapshot.fromJson(Map<String, dynamic> json) => GridSnapshot(
        timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0,
        buses: (json['buses'] as List? ?? [])
            .map((b) => GridBus.fromJson(b as Map<String, dynamic>))
            .toList(),
      );

  double get totalLoad => buses.fold(0.0, (sum, b) => sum + b.consumption);
  double get avgVoltage => buses.isEmpty ? 0 : buses.fold(0.0, (s, b) => s + b.voltage) / buses.length;
  double get avgCurrent => buses.isEmpty ? 0 : buses.fold(0.0, (s, b) => s + b.current) / buses.length;
  double get avgFrequency => buses.isEmpty ? 0 : buses.fold(0.0, (s, b) => s + b.frequency) / buses.length;
  List<GridBus> get attacked => buses.where((b) => b.isAttacked).toList();
}
