import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/detection.dart';
import '../models/model_status.dart';
import '../repositories/smart_grid_repository.dart';

class ScorePoint {
  final int t;
  final double score;
  final double threshold;
  ScorePoint(this.t, this.score, this.threshold);
}

/// Mirrors the web AI Detection page exactly: streams real bus-1 readings
/// into POST /api/detect every 1.5s to build a live sequence buffer, then
/// shows the model's real output — same feed cadence, same field mapping.
class AiDetectionViewModel extends ChangeNotifier {
  final SmartGridRepository repo;
  AiDetectionViewModel(this.repo) {
    _loadModelStatus();
  }

  static const _meterId = 'SM_MOBILE_LIVE';
  static const _zone = 'Zone A';

  ModelStatus? model;
  DetectionResult? latest;
  final List<ScorePoint> history = [];
  bool feeding = false;
  Timer? _feedTimer;
  int _tick = 0;

  Future<void> _loadModelStatus() async {
    try {
      model = await repo.getModelStatus();
      notifyListeners();
    } catch (_) {/* surfaced via detection errors instead */}
  }

  Future<void> refreshModelStatus() => _loadModelStatus();

  void toggleFeed() {
    feeding = !feeding;
    if (feeding) {
      _feedTimer = Timer.periodic(const Duration(milliseconds: 1500), (_) => _tickOnce());
    } else {
      _feedTimer?.cancel();
    }
    notifyListeners();
  }

  Future<void> _tickOnce() async {
    try {
      final grid = await repo.getGrid();
      if (grid.buses.isEmpty) return;
      final bus = grid.buses.first;
      _tick += 1;
      final reading = {
        'meter_id': _meterId,
        'timestamp': DateTime.now().add(Duration(minutes: _tick * 2)).toIso8601String(),
        'consommation_kw': bus.consumption,
        'tension_v': bus.voltage * 230,
        'courant_a': bus.current,
        'power_factor': 0.91,
        'frequency_hz': bus.frequency,
        'zone': _zone,
        'type': bus.consumerType == 'residential'
            ? 'residentiel'
            : bus.consumerType == 'commercial'
                ? 'commercial'
                : 'industriel',
      };
      final result = await repo.detect(reading);
      latest = result;
      if (!result.isBuffering) {
        history.add(ScorePoint(_tick, result.anomalyScore, result.threshold));
        if (history.length > 40) history.removeAt(0);
      }
      notifyListeners();
    } catch (_) {
      // transient — next tick retries, same as the web page's behavior
    }
  }

  @override
  void dispose() {
    _feedTimer?.cancel();
    super.dispose();
  }
}
