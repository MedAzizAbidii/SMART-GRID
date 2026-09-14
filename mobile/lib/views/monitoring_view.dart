import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/monitoring_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/sparkline.dart';

class MonitoringView extends StatelessWidget {
  const MonitoringView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<MonitoringViewModel>();

    return Scaffold(
      appBar: AppBar(title: const Text('Real-Time Monitoring')),
      body: vm.loading
          ? const LoadingView()
          : vm.error != null
              ? ErrorView(message: vm.error!)
              : RefreshIndicator(
                  onRefresh: vm.refresh,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: vm.all.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) {
                      final s = vm.all[i];
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          child: Row(
                            children: [
                              Expanded(
                                flex: 2,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(s.label, style: const TextStyle(color: AppColors.textMuted, fontSize: 11, fontWeight: FontWeight.w600)),
                                    const SizedBox(height: 4),
                                    Text(
                                      s.latest != null ? '${s.latest!.toStringAsFixed(s.latest!.abs() < 10 ? 3 : 1)} ${s.unit}' : '—',
                                      style: const TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w700),
                                    ),
                                  ],
                                ),
                              ),
                              Expanded(
                                flex: 3,
                                child: Sparkline(data: s.history, color: AppColors.primary, height: 34),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
