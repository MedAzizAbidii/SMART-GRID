import '../models/alert.dart';
import '../models/blockchain.dart';
import '../models/grid.dart';
import '../models/health.dart';
import '../models/model_status.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

/// Home screen state: the same 4 pillars the web dashboard leads with
/// (grid / AI / blockchain / threat), plus overview KPIs, all from real
/// endpoints polled in parallel.
class DashboardViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  DashboardViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 8);

  HealthStatus? health;
  ModelStatus? model;
  BlockchainStatus? chain;
  GridSnapshot? grid;
  AlertsSnapshot? alerts;

  bool get connected => error == null && health != null;
  bool get gridOk => grid != null && grid!.attacked.isEmpty;
  bool get aiRunning => model?.detector.loaded ?? false;
  bool get chainValid => chain?.valid ?? false;
  int get activeAlertCount => alerts?.count ?? 0;
  int get totalMeters => grid?.buses.length ?? 0;
  double get powerDemandKw => grid?.totalLoad ?? 0;
  double? get aiConfidencePct =>
      model?.championMetrics.rocAuc != null ? model!.championMetrics.rocAuc! * 100 : null;

  /// Derived security score (0-100), transparent formula: starts at 100,
  /// loses points for each currently-attacked bus and for AI/blockchain
  /// being down — not a fabricated headline number, a documented one.
  int get securityScore {
    var score = 100;
    final attacked = grid?.attacked.length ?? 0;
    score -= attacked * 8;
    if (!aiRunning) score -= 15;
    if (!chainValid) score -= 10;
    return score.clamp(0, 100);
  }

  String get threatLevel {
    final attacked = grid?.attacked.length ?? 0;
    if (attacked > 0) return 'High';
    if (activeAlertCount > 0) return 'Medium';
    return 'Low';
  }

  @override
  Future<void> fetch() async {
    final results = await Future.wait([
      repo.getHealth(),
      repo.getModelStatus(),
      repo.getBlockchainStatus(),
      repo.getGrid(),
      repo.getAlerts(),
    ]);
    health = results[0] as HealthStatus;
    model = results[1] as ModelStatus;
    chain = results[2] as BlockchainStatus;
    grid = results[3] as GridSnapshot;
    alerts = results[4] as AlertsSnapshot;
  }
}
