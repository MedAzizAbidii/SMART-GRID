import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_client.dart';
import '../core/routes.dart';
import '../models/user.dart';
import '../theme/app_theme.dart';
import '../viewmodels/auth_viewmodel.dart';
import 'settings_view.dart';

class MoreView extends StatelessWidget {
  const MoreView({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthViewModel>();
    final user = auth.user;

    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: AppColors.dim(AppColors.primary),
                    child: Text((user?.username ?? '?').substring(0, 1).toUpperCase(),
                        style: const TextStyle(color: AppColors.primary, fontSize: 18, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(user?.fullName.isNotEmpty == true ? user!.fullName : (user?.username ?? '—'),
                            style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 15)),
                        Text(user != null ? roleLabel(user.role) : '', style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                      ],
                    ),
                  ),
                  Container(width: 8, height: 8, decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          _menuItem(context, Icons.link, 'Blockchain Explorer', () => AppRoutes.pushBlockchain(context)),
          _menuItem(context, Icons.lightbulb_outline, 'AI Explainability', () => AppRoutes.pushExplainableAi(context)),
          _menuItem(context, Icons.monitor_heart_outlined, 'Real-Time Monitoring', () => AppRoutes.pushMonitoring(context)),
          _menuItem(context, Icons.bar_chart_outlined, 'Performance', () => _showPerformanceInfo(context)),
          if (auth.isAdmin) _menuItem(context, Icons.group_outlined, 'Users', () => AppRoutes.pushUsers(context)),
          _menuItem(context, Icons.settings_outlined, 'Settings', () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsView()))),
          _menuItem(context, Icons.help_outline, 'Help & Support', () => _showHelp(context)),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => auth.logout(),
              icon: const Icon(Icons.logout, size: 18, color: AppColors.critical),
              label: const Text('Sign out', style: TextStyle(color: AppColors.critical)),
              style: OutlinedButton.styleFrom(side: const BorderSide(color: AppColors.critical), padding: const EdgeInsets.symmetric(vertical: 12)),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: Text('v1.0.0-thesis · ${ApiClient.baseUrl}',
                style: const TextStyle(color: AppColors.textMuted, fontSize: 10)),
          ),
        ],
      ),
    );
  }

  Widget _menuItem(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon, color: AppColors.textSecondary, size: 20),
        title: Text(label, style: const TextStyle(color: AppColors.textPrimary, fontSize: 14, fontWeight: FontWeight.w500)),
        trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted, size: 18),
        onTap: onTap,
      ),
    );
  }

  void _showPerformanceInfo(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.card,
        title: const Text('Performance', style: TextStyle(color: AppColors.textPrimary)),
        content: const Text(
          'Full latency/throughput/concurrency profiling was run as a dedicated project phase (Phase 7) '
          'and is published as a static report — it is not re-run live from this screen. '
          'Headline result: overall performance score 62.2/100, profiled across latency, resource usage, '
          'throughput and concurrency (1-1000 simulated requests).',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13, height: 1.5),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close'))],
      ),
    );
  }

  void _showHelp(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.card,
        title: const Text('Help & Support', style: TextStyle(color: AppColors.textPrimary)),
        content: const Text(
          'GridSentinel is the mobile client for the Smart Grid Cybersecurity Platform PFE project — '
          'AI-based anomaly detection, a Proof-of-Authority blockchain ledger, and an optional real '
          'Ethereum (Sepolia) anchor, consuming the exact same backend as the web dashboard.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13, height: 1.5),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close'))],
      ),
    );
  }
}
