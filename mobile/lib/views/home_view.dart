import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/routes.dart';
import '../models/user.dart';
import '../theme/app_theme.dart';
import '../viewmodels/auth_viewmodel.dart';
import '../viewmodels/dashboard_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';

class HomeView extends StatelessWidget {
  const HomeView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DashboardViewModel>();
    final auth = context.watch<AuthViewModel>();

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 30, height: 30,
              decoration: BoxDecoration(color: AppColors.dim(AppColors.primary), borderRadius: BorderRadius.circular(8)),
              child: const Icon(Icons.bolt, color: AppColors.primary, size: 16),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('GridSentinel', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                Text('Smart Grid Cybersecurity', style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
              ],
            ),
          ],
        ),
        actions: [
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(icon: const Icon(Icons.notifications_outlined), onPressed: () => AppRoutes.pushAlerts(context)),
              if (vm.activeAlertCount > 0)
                Positioned(
                  top: 10, right: 10,
                  child: Container(
                    width: 8, height: 8,
                    decoration: const BoxDecoration(color: AppColors.critical, shape: BoxShape.circle),
                  ),
                ),
            ],
          ),
        ],
      ),
      body: vm.loading
          ? const LoadingView()
          : RefreshIndicator(
              onRefresh: vm.refresh,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (vm.error != null)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(color: AppColors.dim(AppColors.critical), borderRadius: BorderRadius.circular(10)),
                      child: Text(vm.error!, style: const TextStyle(color: AppColors.critical)),
                    ),

                  // Grid Status + Security Score
                  Row(
                    children: [
                      Expanded(
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('GRID STATUS', style: TextStyle(color: AppColors.textMuted, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
                                const SizedBox(height: 10),
                                Row(
                                  children: [
                                    Icon(Icons.circle, size: 10, color: vm.gridOk ? AppColors.success : AppColors.critical),
                                    const SizedBox(width: 6),
                                    Text(vm.gridOk ? 'Operational' : 'Degraded', style: const TextStyle(
                                        color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 15)),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(vm.gridOk ? 'All systems normal' : '${vm.grid?.attacked.length ?? 0} smart meter(s) under attack',
                                    style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              children: [
                                const Text('SECURITY SCORE', style: TextStyle(color: AppColors.textMuted, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
                                const SizedBox(height: 8),
                                Text('${vm.securityScore}', style: TextStyle(
                                    color: _scoreColor(vm.securityScore), fontSize: 28, fontWeight: FontWeight.w800)),
                                Text(_scoreLabel(vm.securityScore), style: TextStyle(color: _scoreColor(vm.securityScore), fontSize: 11, fontWeight: FontWeight.w600)),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Pills row
                  Row(
                    children: [
                      Expanded(child: _pillCard(context, 'AI ENGINE', vm.aiRunning ? 'Running' : 'Stopped', vm.aiRunning ? 'success' : 'critical', Icons.psychology_outlined, () => AppRoutes.pushAiDetection(context))),
                      const SizedBox(width: 8),
                      Expanded(child: _pillCard(context, 'BLOCKCHAIN', vm.chainValid ? 'Verified' : 'Issues', vm.chainValid ? 'success' : 'warning', Icons.link, () => AppRoutes.pushBlockchain(context))),
                      const SizedBox(width: 8),
                      Expanded(child: _pillCard(context, 'THREAT', vm.threatLevel, vm.threatLevel == 'High' ? 'critical' : vm.threatLevel == 'Medium' ? 'warning' : 'success', Icons.shield_outlined, () => AppRoutes.pushCybersecurity(context))),
                    ],
                  ),
                  const SizedBox(height: 20),

                  SectionHeader(title: 'Overview', action: Text(
                      vm.connected ? 'Live · updated now' : 'Offline',
                      style: TextStyle(color: vm.connected ? AppColors.success : AppColors.critical, fontSize: 11, fontWeight: FontWeight.w600))),
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 1.5,
                    children: [
                      GestureDetector(
                        onTap: () => AppRoutes.pushMeters(context),
                        child: StatusCard(icon: Icons.sensors, label: 'Total Smart Meters', value: '${vm.totalMeters}'),
                      ),
                      GestureDetector(
                        onTap: () => AppRoutes.pushMonitoring(context),
                        child: StatusCard(icon: Icons.bolt, label: 'Power Demand', value: '${vm.powerDemandKw.toStringAsFixed(1)} kW', tone: 'info'),
                      ),
                      GestureDetector(
                        onTap: () => AppRoutes.pushAlerts(context),
                        child: StatusCard(icon: Icons.warning_amber_rounded, label: 'Active Alerts', value: '${vm.activeAlertCount}', tone: vm.activeAlertCount > 0 ? 'warning' : 'success'),
                      ),
                      GestureDetector(
                        onTap: () => AppRoutes.pushAiDetection(context),
                        child: StatusCard(icon: Icons.auto_awesome, label: 'AI Confidence', value: vm.aiConfidencePct != null ? '${vm.aiConfidencePct!.toStringAsFixed(1)}%' : '—', tone: 'primary'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  SectionHeader(title: 'Quick Access'),
                  Wrap(
                    spacing: 10, runSpacing: 10,
                    children: [
                      _quickTile(context, Icons.sensors, 'Smart Meters', () => AppRoutes.pushMeters(context)),
                      _quickTile(context, Icons.receipt_long, 'Electricity Theft', () => AppRoutes.pushTheft(context)),
                      _quickTile(context, Icons.lightbulb_outline, 'Explainable AI', () => AppRoutes.pushExplainableAi(context)),
                      _quickTile(context, Icons.monitor_heart_outlined, 'Monitoring', () => AppRoutes.pushMonitoring(context)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('Signed in as ${auth.user?.username ?? "—"} · ${auth.user != null ? roleLabel(auth.user!.role) : ""}',
                      style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                ],
              ),
            ),
    );
  }

  Widget _pillCard(BuildContext context, String label, String value, String tone, IconData icon, VoidCallback onTap) {
    final color = toneColor(tone);
    return GestureDetector(
      onTap: onTap,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
          child: Column(
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(height: 6),
              Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 0.3)),
              const SizedBox(height: 2),
              Text(value, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _quickTile(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: (MediaQuery.of(context).size.width - 16 * 2 - 10) / 2,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppColors.primary, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12, fontWeight: FontWeight.w600))),
          ],
        ),
      ),
    );
  }

  Color _scoreColor(int score) {
    if (score >= 85) return AppColors.success;
    if (score >= 60) return AppColors.warning;
    return AppColors.critical;
  }

  String _scoreLabel(int score) {
    if (score >= 85) return 'Excellent';
    if (score >= 60) return 'Fair';
    return 'At Risk';
  }
}
