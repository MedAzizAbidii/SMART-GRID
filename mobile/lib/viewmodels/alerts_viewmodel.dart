import '../models/alert.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

class AlertsViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  AlertsViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 5);

  AlertsSnapshot? snapshot;
  String severityFilter = 'all'; // all | critical | high | medium | low

  List<GridAlert> get filtered {
    final list = (snapshot?.alerts ?? []).reversed.toList(); // newest first
    if (severityFilter == 'all') return list;
    return list.where((a) => a.severityTier == severityFilter).toList();
  }

  Map<String, int> get countsByTier {
    final counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0};
    for (final a in snapshot?.alerts ?? <GridAlert>[]) {
      counts[a.severityTier] = (counts[a.severityTier] ?? 0) + 1;
    }
    return counts;
  }

  void setFilter(String tier) {
    severityFilter = tier;
    notifyListeners();
  }

  @override
  Future<void> fetch() async {
    snapshot = await repo.getAlerts();
  }
}
