/// Mirrors one entry of GET /api/alerts' "alerts" array. The backend does
/// not send a severity field, so `severityTier` derives one transparently
/// from `confidence` — the same honest-derivation approach used for KPI
/// tones in the web dashboard (never a fabricated number).
class GridAlert {
  final double timestamp;
  final int busId;
  final String attackType;
  final double confidence;
  final String description;

  GridAlert({
    required this.timestamp,
    required this.busId,
    required this.attackType,
    required this.confidence,
    required this.description,
  });

  String get id => '$busId-$timestamp';
  String get meterId => 'SM_${busId.toString().padLeft(2, '0')}';

  /// Derived, not sent by the backend: confidence-bucketed severity.
  String get severityTier {
    if (confidence >= 0.85) return 'critical';
    if (confidence >= 0.7) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  }

  DateTime get dateTime => DateTime.fromMillisecondsSinceEpoch((timestamp * 1000).round());

  factory GridAlert.fromJson(Map<String, dynamic> json) => GridAlert(
        timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0,
        busId: (json['bus_id'] as num?)?.toInt() ?? 0,
        attackType: json['attack_type'] as String? ?? 'unknown',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        description: json['description'] as String? ?? '',
      );
}

class AlertsSnapshot {
  final int count;
  final List<GridAlert> alerts;

  AlertsSnapshot({required this.count, required this.alerts});

  factory AlertsSnapshot.fromJson(Map<String, dynamic> json) => AlertsSnapshot(
        count: (json['count'] as num?)?.toInt() ?? 0,
        alerts: (json['alerts'] as List? ?? [])
            .map((a) => GridAlert.fromJson(a as Map<String, dynamic>))
            .toList(),
      );
}
