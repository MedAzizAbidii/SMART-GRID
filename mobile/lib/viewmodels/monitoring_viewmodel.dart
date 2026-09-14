import '../models/grid.dart';
import '../models/health.dart';
import '../models/model_status.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

/// A named, real-valued time series with a small rolling client-side
/// history — mirrors the web dashboard's useHistorySeries hook so
/// sparklines show genuine session data, never fabricated series.
class MetricSeries {
  final String label;
  final String unit;
  final List<double> history = [];
  double? latest;

  MetricSeries(this.label, this.unit);

  void push(double? value, {int maxLen = 30}) {
    if (value == null || value.isNaN) return;
    latest = value;
    if (history.isEmpty || history.last != value) {
      history.add(value);
      if (history.length > maxLen) history.removeAt(0);
    }
  }
}

class MonitoringViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  MonitoringViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 2);

  final power = MetricSeries('Power Demand', 'kW');
  final voltage = MetricSeries('Avg Voltage', 'pu');
  final current = MetricSeries('Avg Current', 'A');
  final frequency = MetricSeries('Avg Frequency', 'Hz');
  final cpu = MetricSeries('CPU Usage', '%');
  final memory = MetricSeries('Memory Usage', '%');
  final aiConfidence = MetricSeries('AI Confidence', '%');
  final inferenceLatency = MetricSeries('Inference Latency', 'ms');

  List<MetricSeries> get all =>
      [power, voltage, current, frequency, cpu, memory, aiConfidence, inferenceLatency];

  @override
  Future<void> fetch() async {
    final GridSnapshot grid = await repo.getGrid();
    final HealthStatus health = await repo.getHealth();
    final ModelStatus model = await repo.getModelStatus();

    power.push(grid.totalLoad);
    voltage.push(grid.avgVoltage);
    current.push(grid.avgCurrent);
    frequency.push(grid.avgFrequency);
    cpu.push(health.cpuPercent);
    memory.push(health.memoryPercent);
    aiConfidence.push(model.championMetrics.rocAuc != null ? model.championMetrics.rocAuc! * 100 : null);
    inferenceLatency.push(model.detector.avgLatencyMs);
  }
}
