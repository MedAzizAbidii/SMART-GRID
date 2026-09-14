import 'package:flutter/foundation.dart';
import '../models/detection.dart';
import '../repositories/smart_grid_repository.dart';

enum XaiTab { features, gradients, attention, shap, breakdown }

/// Mirrors the web Explainable AI page: runs 9 consecutive real readings
/// from bus 1 through /api/detect (filling the model's 8-step sequence
/// buffer), then explains the final real prediction. The SHAP tab is
/// explicitly illustrative-only here too — SHAP is offline-only in
/// production (too slow for the real-time path), exactly as documented on
/// the web page; this mirrors that honesty rather than pretending it's live.
class ExplainableAiViewModel extends ChangeNotifier {
  final SmartGridRepository repo;
  ExplainableAiViewModel(this.repo);

  static const _meterId = 'SM_MOBILE_XAI';

  XaiTab tab = XaiTab.features;
  DetectionResult? result;
  bool running = false;
  String? error;
  int _tick = 0;

  bool get hasResult => result != null && !result!.isBuffering;

  static final sampleShapFeatures = [
    FeatureContribution(feature: 'tension_v_rolling_std_6', contribution: 0.31),
    FeatureContribution(feature: 'consommation_kw', contribution: 0.24),
    FeatureContribution(feature: 'zone_consumption_mean', contribution: 0.18),
  ];

  void setTab(XaiTab t) {
    tab = t;
    notifyListeners();
  }

  Future<void> runExplanation() async {
    running = true;
    error = null;
    notifyListeners();
    try {
      final grid = await repo.getGrid();
      if (grid.buses.isEmpty) throw Exception('no grid data');
      final bus = grid.buses.first;
      DetectionResult? last;
      for (var i = 0; i < 9; i++) {
        _tick += 1;
        final reading = {
          'meter_id': _meterId,
          'timestamp': DateTime.now().add(Duration(minutes: _tick * 2)).toIso8601String(),
          'consommation_kw': bus.consumption * (1 + i * 0.01),
          'tension_v': bus.voltage * 230,
          'courant_a': bus.current,
          'power_factor': 0.91,
          'frequency_hz': bus.frequency,
          'zone': 'Zone A',
          'type': bus.consumerType == 'residential'
              ? 'residentiel'
              : bus.consumerType == 'commercial'
                  ? 'commercial'
                  : 'industriel',
        };
        last = await repo.detect(reading);
      }
      result = last;
    } catch (_) {
      error = 'Cannot reach server or grid feed unavailable';
    } finally {
      running = false;
      notifyListeners();
    }
  }
}
