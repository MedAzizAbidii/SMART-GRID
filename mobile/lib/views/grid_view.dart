import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/grid_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/grid_topology_view.dart';
import '../widgets/status_card.dart';

const _layers = [
  ('all', 'All'), ('residential', 'Residential'), ('commercial', 'Commercial'), ('industrial', 'Industrial'),
];

class GridScreenView extends StatelessWidget {
  const GridScreenView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<GridViewModel>();
    final selected = vm.selectedBus;

    return Scaffold(
      appBar: AppBar(title: const Text('Smart Grid')),
      body: vm.loading
          ? const LoadingView()
          : vm.error != null
              ? ErrorView(message: vm.error!)
              : RefreshIndicator(
                  onRefresh: vm.refresh,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      SizedBox(
                        height: 34,
                        child: ListView(
                          scrollDirection: Axis.horizontal,
                          children: [
                            for (final (value, label) in _layers) ...[
                              FilterChip2(label: label, selected: vm.layerFilter == value, onTap: () => vm.setLayer(value)),
                              const SizedBox(width: 8),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(8),
                          child: GridTopologyView(
                            buses: vm.filteredBuses,
                            selectedBusId: vm.selectedBusId,
                            onSelect: vm.selectBus,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      SectionHeader(title: selected != null ? selected.meterId : 'Select a node'),
                      if (selected == null)
                        const Card(
                          child: Padding(
                            padding: EdgeInsets.all(20),
                            child: Center(child: Text('Tap a node on the map above for its live readings',
                                style: TextStyle(color: AppColors.textMuted))),
                          ),
                        )
                      else
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              children: [
                                _row('Consumer type', selected.consumerType),
                                _row('Voltage', '${selected.voltage.toStringAsFixed(4)} pu'),
                                _row('Current', '${selected.current.toStringAsFixed(2)} A'),
                                _row('Frequency', '${selected.frequency.toStringAsFixed(3)} Hz'),
                                _row('Consumption', '${selected.consumption.toStringAsFixed(2)} kW'),
                                Padding(
                                  padding: const EdgeInsets.only(top: 6),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      const Text('Status', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                                      StatusBadge(
                                        label: selected.isAttacked ? selected.attackType.toUpperCase() : 'NORMAL',
                                        tone: selected.isAttacked ? 'critical' : 'success',
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
            Text(value, style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 13)),
          ],
        ),
      );
}
