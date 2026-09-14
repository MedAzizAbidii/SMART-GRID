/// Mirrors GET /health/detailed on api_server.py exactly.
class HealthStatus {
  final String status;
  final double uptimeSeconds;
  final double? cpuPercent;
  final double? memoryMb;
  final double? memoryPercent;
  final bool modelLoaded;
  final double? modelAvgLatencyMs;
  final bool blockchainAvailable;
  final bool blockchainValid;
  final int blockchainBlocks;

  HealthStatus({
    required this.status,
    required this.uptimeSeconds,
    this.cpuPercent,
    this.memoryMb,
    this.memoryPercent,
    required this.modelLoaded,
    this.modelAvgLatencyMs,
    required this.blockchainAvailable,
    required this.blockchainValid,
    required this.blockchainBlocks,
  });

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    final resources = json['resources'] as Map<String, dynamic>?;
    final model = json['model'] as Map<String, dynamic>?;
    final chain = json['blockchain'] as Map<String, dynamic>?;
    return HealthStatus(
      status: json['status'] as String? ?? 'unknown',
      uptimeSeconds: (json['uptime_seconds'] as num?)?.toDouble() ?? 0,
      cpuPercent: (resources?['cpu_percent'] as num?)?.toDouble(),
      memoryMb: (resources?['memory_mb'] as num?)?.toDouble(),
      memoryPercent: (resources?['memory_percent'] as num?)?.toDouble(),
      modelLoaded: model?['loaded'] == true,
      modelAvgLatencyMs: (model?['avg_latency_ms'] as num?)?.toDouble(),
      blockchainAvailable: chain?['available'] == true,
      blockchainValid: chain?['valid'] == true,
      blockchainBlocks: (chain?['blocks'] as num?)?.toInt() ?? 0,
    );
  }
}
