/// Mirrors GET /api/model/status and GET /api/model/registry.
class ChampionMetrics {
  final double? accuracy;
  final double? precision;
  final double? recall;
  final double? f1Score;
  final double? rocAuc;

  ChampionMetrics({this.accuracy, this.precision, this.recall, this.f1Score, this.rocAuc});

  factory ChampionMetrics.fromJson(Map<String, dynamic>? json) {
    if (json == null) return ChampionMetrics();
    return ChampionMetrics(
      accuracy: (json['accuracy'] as num?)?.toDouble(),
      precision: (json['precision'] as num?)?.toDouble(),
      recall: (json['recall'] as num?)?.toDouble(),
      f1Score: (json['f1_score'] as num?)?.toDouble(),
      rocAuc: (json['roc_auc'] as num?)?.toDouble(),
    );
  }

  bool get hasData => rocAuc != null;
}

class DetectorInfo {
  final bool loaded;
  final double? avgLatencyMs;
  final int? seqLen;
  final int? featureCount;
  final double? globalThreshold;

  DetectorInfo({required this.loaded, this.avgLatencyMs, this.seqLen, this.featureCount, this.globalThreshold});

  factory DetectorInfo.fromJson(Map<String, dynamic>? json) {
    if (json == null) return DetectorInfo(loaded: false);
    return DetectorInfo(
      loaded: json['loaded'] == true,
      avgLatencyMs: (json['avg_latency_ms'] as num?)?.toDouble(),
      seqLen: (json['seq_len'] as num?)?.toInt(),
      featureCount: (json['feature_count'] as num?)?.toInt(),
      globalThreshold: (json['global_threshold'] as num?)?.toDouble(),
    );
  }
}

class ModelStatus {
  final DetectorInfo detector;
  final ChampionMetrics championMetrics;
  final String? championVersion;
  final int totalVersions;

  ModelStatus({
    required this.detector,
    required this.championMetrics,
    this.championVersion,
    this.totalVersions = 0,
  });

  factory ModelStatus.fromJson(Map<String, dynamic> json) {
    final registry = json['registry'] as Map<String, dynamic>?;
    return ModelStatus(
      detector: DetectorInfo.fromJson(json['detector'] as Map<String, dynamic>?),
      championMetrics: ChampionMetrics.fromJson(registry?['champion_metrics'] as Map<String, dynamic>?),
      championVersion: registry?['champion_version'] as String?,
      totalVersions: (registry?['total_versions'] as num?)?.toInt() ?? 0,
    );
  }
}

class ModelVersion {
  final String version;
  final String tag;
  final String status;
  final ChampionMetrics metrics;

  ModelVersion({required this.version, required this.tag, required this.status, required this.metrics});

  factory ModelVersion.fromJson(Map<String, dynamic> json) => ModelVersion(
        version: json['version'] as String? ?? '',
        tag: json['tag'] as String? ?? '',
        status: json['status'] as String? ?? '',
        metrics: ChampionMetrics.fromJson(json['metrics'] as Map<String, dynamic>?),
      );
}
