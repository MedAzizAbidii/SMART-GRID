import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/meters_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';

const _filters = [
  (MeterFilter.all, 'All Meters'),
  (MeterFilter.online, 'Online'),
  (MeterFilter.offline, 'Offline'),
  (MeterFilter.highRisk, 'High Risk'),
];

class MetersView extends StatelessWidget {
  const MetersView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<MetersViewModel>();

    return Scaffold(
      appBar: AppBar(title: const Text('Smart Meters')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            SearchField(hint: 'Search meter ID, type...', onChanged: vm.setQuery),
            const SizedBox(height: 12),
            SizedBox(
              height: 34,
              child: ListView(
                scrollDirection: Axis.horizontal,
                children: [
                  for (final (value, label) in _filters) ...[
                    FilterChip2(label: label, selected: vm.filter == value, onTap: () => vm.setFilter(value)),
                    const SizedBox(width: 8),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: vm.loading
                  ? const LoadingView()
                  : vm.error != null
                      ? ErrorView(message: vm.error!)
                      : vm.results.isEmpty
                          ? const EmptyView(message: 'No meters match this filter')
                          : RefreshIndicator(
                              onRefresh: vm.refresh,
                              child: ListView.separated(
                                itemCount: vm.results.length,
                                separatorBuilder: (_, _) => const SizedBox(height: 8),
                                itemBuilder: (context, i) {
                                  final m = vm.results[i];
                                  return Card(
                                    child: ListTile(
                                      leading: Container(
                                        width: 38, height: 38,
                                        decoration: BoxDecoration(
                                          color: AppColors.dim(m.isAttacked ? AppColors.critical : AppColors.success),
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        child: Icon(Icons.sensors,
                                            color: m.isAttacked ? AppColors.critical : AppColors.success, size: 18),
                                      ),
                                      title: Text(m.meterId, style: const TextStyle(
                                          color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 13)),
                                      subtitle: Text('${m.consumerType} · ${m.voltage.toStringAsFixed(0)} V · ${m.consumption.toStringAsFixed(2)} kW',
                                          style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                      trailing: StatusBadge(
                                        label: m.isAttacked ? 'High Risk' : 'Online',
                                        tone: m.isAttacked ? 'critical' : 'success',
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
            ),
          ],
        ),
      ),
    );
  }
}
