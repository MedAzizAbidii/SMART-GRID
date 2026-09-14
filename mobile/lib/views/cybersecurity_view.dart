import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/cybersecurity_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';

class CybersecurityView extends StatelessWidget {
  const CybersecurityView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<CybersecurityViewModel>();

    return Scaffold(
      appBar: AppBar(title: const Text('Cybersecurity')),
      body: vm.loading
          ? const LoadingView()
          : vm.error != null
              ? ErrorView(message: vm.error!)
              : RefreshIndicator(
                  onRefresh: vm.refresh,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      GridView.count(
                        crossAxisCount: 2,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 12,
                        childAspectRatio: 1.5,
                        children: [
                          StatusCard(
                            icon: Icons.warning_amber_rounded,
                            label: 'Live Attacks',
                            value: '${vm.liveAttacks}',
                            tone: vm.liveAttacks > 0 ? 'critical' : 'success',
                          ),
                          StatusCard(
                            icon: Icons.notifications_active_outlined,
                            label: 'Alerts (session)',
                            value: '${vm.totalSessionAlerts}',
                            tone: 'warning',
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const SectionHeader(title: 'Attack Type Distribution (session)'),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: vm.attackTypeDistribution.isEmpty
                              ? const Text('No attacks recorded yet in this session', style: TextStyle(color: AppColors.textMuted))
                              : Column(
                                  children: vm.attackTypeDistribution.entries.map((e) {
                                    final total = vm.totalSessionAlerts == 0 ? 1 : vm.totalSessionAlerts;
                                    final pct = e.value / total * 100;
                                    return Padding(
                                      padding: const EdgeInsets.only(bottom: 10),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                            children: [
                                              Text(e.key, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                                              Text('${e.value} (${pct.toStringAsFixed(0)}%)', style: const TextStyle(color: AppColors.textPrimary, fontSize: 12, fontWeight: FontWeight.w600)),
                                            ],
                                          ),
                                          const SizedBox(height: 4),
                                          ProgressBar(value: pct, tone: 'critical'),
                                        ],
                                      ),
                                    );
                                  }).toList(),
                                ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      const SectionHeader(title: 'Severity Distribution (session)'),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Row(
                            children: vm.severityDistribution.entries.map((e) {
                              return Expanded(
                                child: Column(
                                  children: [
                                    Text('${e.value}', style: TextStyle(
                                        color: toneColor(_tierTone(e.key)), fontSize: 20, fontWeight: FontWeight.w800)),
                                    const SizedBox(height: 4),
                                    Text(e.key, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                                  ],
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  String _tierTone(String tier) {
    switch (tier) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      default:
        return 'success';
    }
  }
}
