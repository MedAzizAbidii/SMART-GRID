import '../models/alert.dart';
import '../models/grid.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

/// Electricity theft/fraud detection — 'fraud' is a real attack type the
/// simulator generates (under-reporting theft, the project's core research
/// focus), so detected count and flagged meters below are real, not
/// fabricated. There is no currency/kWh-recovered tracking in the backend,
/// so no dollar or MWh figures are shown here — unlike some reference UIs
/// that invent a national-scale loss total, this screen only shows what
/// the model actually detected.
class TheftViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  TheftViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 5);

  GridSnapshot? grid;
  AlertsSnapshot? alerts;

  List<GridBus> get flaggedMeters => grid?.buses.where((b) => b.attackType == 'fraud').toList() ?? [];

  List<GridAlert> get fraudAlerts =>
      (alerts?.alerts ?? []).where((a) => a.attackType == 'fraud').toList().reversed.toList();

  int get detectedCount => flaggedMeters.length;

  @override
  Future<void> fetch() async {
    final results = await Future.wait([repo.getGrid(), repo.getAlerts()]);
    grid = results[0] as GridSnapshot;
    alerts = results[1] as AlertsSnapshot;
  }
}
