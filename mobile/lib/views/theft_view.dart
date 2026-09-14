import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/theft_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';

class TheftView extends StatelessWidget {
  const TheftView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<TheftViewModel>();

    return Scaffold(
      appBar: AppBar(title: const Text('Electricity Theft')),
      body: vm.loading
          ? const LoadingView()
          : vm.error != null
              ? ErrorView(message: vm.error!)
              : RefreshIndicator(
                  onRefresh: vm.refresh,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      const Text(
                        "'Fraud' (under-reporting theft) is a real attack type this simulator generates — every number below reflects the model's actual detections, not a projected national loss figure.",
                        style: TextStyle(color: AppColors.textMuted, fontSize: 12, height: 1.4),
                      ),
                      const SizedBox(height: 14),
                      StatusCard(
                        icon: Icons.receipt_long_outlined,
                        label: 'Fraud-Flagged Meters (live)',
                        value: '${vm.detectedCount}',
                        tone: vm.detectedCount > 0 ? 'warning' : 'success',
                      ),
                      const SizedBox(height: 16),
                      const SectionHeader(title: 'Flagged Meters'),
                      if (vm.flaggedMeters.isEmpty)
                        const Card(child: Padding(padding: EdgeInsets.all(20),
                            child: Center(child: Text('No fraud-pattern meters detected right now', style: TextStyle(color: AppColors.textMuted)))))
                      else
                        ...vm.flaggedMeters.map((m) => Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: const Icon(Icons.receipt_long, color: AppColors.warning),
                                title: Text(m.meterId, style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 13)),
                                subtitle: Text('${m.consumerType} · ${m.consumption.toStringAsFixed(2)} kW reported',
                                    style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                trailing: const StatusBadge(label: 'FRAUD', tone: 'warning'),
                              ),
                            )),
                      const SizedBox(height: 16),
                      const SectionHeader(title: 'Recent Fraud Alerts (session)'),
                      if (vm.fraudAlerts.isEmpty)
                        const Card(child: Padding(padding: EdgeInsets.all(20),
                            child: Center(child: Text('No fraud alerts recorded yet in this session', style: TextStyle(color: AppColors.textMuted)))))
                      else
                        ...vm.fraudAlerts.take(10).map((a) => Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: const Icon(Icons.history, color: AppColors.textMuted),
                                title: Text(a.meterId, style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 13)),
                                subtitle: Text(a.description, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                trailing: Text('${(a.confidence * 100).round()}%', style: const TextStyle(color: AppColors.warning, fontWeight: FontWeight.w700)),
                              ),
                            )),
                    ],
                  ),
                ),
    );
  }
}
