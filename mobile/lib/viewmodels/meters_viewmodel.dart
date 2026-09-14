import '../models/grid.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

enum MeterFilter { all, online, offline, highRisk }

/// Smart Meters list — each of the simulator's real buses styled as a
/// meter (SM_XX). There is no real "offline meter" concept in the
/// simulator (every bus reports every tick), so that filter honestly
/// returns empty rather than inventing fake offline devices.
class MetersViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  MetersViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 3);

  GridSnapshot? grid;
  String query = '';
  MeterFilter filter = MeterFilter.all;

  List<GridBus> get results {
    var buses = grid?.buses ?? [];
    switch (filter) {
      case MeterFilter.offline:
        buses = const []; // no real offline concept in the simulator — honest empty, not fabricated
      case MeterFilter.highRisk:
        buses = buses.where((b) => b.isAttacked).toList();
      case MeterFilter.online:
      case MeterFilter.all:
        break; // every returned bus is, by definition, currently reporting
    }
    if (query.trim().isEmpty) return buses;
    final q = query.trim().toLowerCase();
    return buses.where((b) => b.meterId.toLowerCase().contains(q) || b.consumerType.toLowerCase().contains(q)).toList();
  }

  void setQuery(String q) {
    query = q;
    notifyListeners();
  }

  void setFilter(MeterFilter f) {
    filter = f;
    notifyListeners();
  }

  @override
  Future<void> fetch() async {
    grid = await repo.getGrid();
  }
}
