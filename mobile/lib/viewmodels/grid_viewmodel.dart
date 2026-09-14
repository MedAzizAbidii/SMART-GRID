import '../models/grid.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

class GridViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  GridViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 2);

  GridSnapshot? grid;
  int? selectedBusId;
  String layerFilter = 'all'; // all | residential | commercial | industrial

  List<GridBus> get filteredBuses {
    final buses = grid?.buses ?? [];
    if (layerFilter == 'all') return buses;
    return buses.where((b) => b.consumerType == layerFilter).toList();
  }

  GridBus? get selectedBus {
    if (selectedBusId == null) return null;
    try {
      return grid?.buses.firstWhere((b) => b.busId == selectedBusId);
    } catch (_) {
      return null;
    }
  }

  void selectBus(int busId) {
    selectedBusId = busId;
    notifyListeners();
  }

  void setLayer(String layer) {
    layerFilter = layer;
    notifyListeners();
  }

  @override
  Future<void> fetch() async {
    grid = await repo.getGrid();
  }
}
