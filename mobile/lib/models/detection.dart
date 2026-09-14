/// Mirrors the response of POST /api/detect exactly — the same shape the
/// web AI Detection / Explainable AI pages consume.
class FeatureContribution {
  final String feature;
  final double contribution;
  FeatureContribution({required this.feature, required this.contribution});

  factory FeatureContribution.fromJson(Map<String, dynamic> json) => FeatureContribution(
        feature: json['feature'] as String? ?? '',
        contribution: (json['contribution'] as num?)?.toDouble() ?? 0,
      );
}

class DetectionResult {
  final String meterId;
  final bool isAnomaly;
  final double anomalyScore;
  final double threshold;
  final double confidence;
  final String attackType;
  final String attackDescription;
  final List<FeatureContribution> topFeatures;
  final int criticalTimestep;
  final int bufferFill;
  final double inferenceMs;
  final String status;
  final bool deduplicated;
  final bool blockchainNotarized;
  final double? v2Score;
  final double? v3Score;
  final bool? v2Alarm;
  final bool? v3Alarm;
  final String? confidenceLabel;

  DetectionResult({
    required this.meterId,
    required this.isAnomaly,
    required this.anomalyScore,
    required this.threshold,
    required this.confidence,
    required this.attackType,
    required this.attackDescription,
    required this.topFeatures,
    required this.criticalTimestep,
    required this.bufferFill,
    required this.inferenceMs,
    required this.status,
    required this.deduplicated,
    required this.blockchainNotarized,
    this.v2Score,
    this.v3Score,
    this.v2Alarm,
    this.v3Alarm,
    this.confidenceLabel,
  });

  bool get isBuffering => status == 'insufficient_data';

  factory DetectionResult.fromJson(Map<String, dynamic> json) => DetectionResult(
        meterId: json['meter_id'] as String? ?? '',
        isAnomaly: json['is_anomaly'] == true,
        anomalyScore: (json['anomaly_score'] as num?)?.toDouble() ?? 0,
        threshold: (json['threshold'] as num?)?.toDouble() ?? 0,
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        attackType: json['attack_type'] as String? ?? 'normal',
        attackDescription: json['attack_description'] as String? ?? '',
        topFeatures: (json['top_features'] as List? ?? [])
            .map((f) => FeatureContribution.fromJson(f as Map<String, dynamic>))
            .toList(),
        criticalTimestep: (json['critical_timestep'] as num?)?.toInt() ?? 0,
        bufferFill: (json['buffer_fill'] as num?)?.toInt() ?? 0,
        inferenceMs: (json['inference_ms'] as num?)?.toDouble() ?? 0,
        status: json['status'] as String? ?? '',
        deduplicated: json['deduplicated'] == true,
        blockchainNotarized: json['blockchain_notarized'] == true,
        v2Score: (json['v2_score'] as num?)?.toDouble(),
        v3Score: (json['v3_score'] as num?)?.toDouble(),
        v2Alarm: json['v2_alarm'] as bool?,
        v3Alarm: json['v3_alarm'] as bool?,
        confidenceLabel: json['confidence_label'] as String?,
      );
}
