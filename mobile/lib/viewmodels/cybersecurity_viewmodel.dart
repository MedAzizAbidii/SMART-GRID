import '../models/alert.dart';
import '../models/grid.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

/// Cybersecurity overview — every number here is either live grid state or
/// an aggregation of this session's real /api/alerts, never a fabricated
/// national-scale figure. Labeled "this session" rather than "24H" since
/// that is honestly what the backend has (no historical alert archive).
class CybersecurityViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  CybersecurityViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 5);

  GridSnapshot? grid;
  AlertsSnapshot? alerts;

  int get liveAttacks => grid?.attacked.length ?? 0;
  int get totalSessionAlerts => alerts?.count ?? 0;

  Map<String, int> get attackTypeDistribution {
    final counts = <String, int>{};
    for (final a in alerts?.alerts ?? <GridAlert>[]) {
      counts[a.attackType] = (counts[a.attackType] ?? 0) + 1;
    }
    return counts;
  }

  Map<String, int> get severityDistribution {
    final counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0};
    for (final a in alerts?.alerts ?? <GridAlert>[]) {
      counts[a.severityTier] = (counts[a.severityTier] ?? 0) + 1;
    }
    return counts;
  }

  @override
  Future<void> fetch() async {
    final results = await Future.wait([repo.getGrid(), repo.getAlerts()]);
    grid = results[0] as GridSnapshot;
    alerts = results[1] as AlertsSnapshot;
  }
}
