import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/alerts_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';
import '../services/firebase_service.dart';
import '../services/cache_service.dart';

const _tiers = [
  ('all', 'All'), ('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low'),
];

class AlertsView extends StatefulWidget {
  const AlertsView({super.key});

  @override
  State<AlertsView> createState() => _AlertsViewState();
}

class _AlertsViewState extends State<AlertsView> {
  late final CacheService _cache;

  @override
  void initState() {
    super.initState();
    _cache = CacheService();
    // Listen for incoming push notifications
    FirebaseService().notificationStream.listen((payload) {
      _cache.cacheAlert(
        '${payload.timestamp.millisecondsSinceEpoch}',
        {
          'title': payload.title,
          'body': payload.body,
          'type': payload.type,
          'data': payload.data,
        },
      );
      // Trigger refresh when new alert arrives
      if (mounted) {
        context.read<AlertsViewModel>().refresh();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<AlertsViewModel>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts Center'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(child: StatusBadge(label: '${vm.snapshot?.count ?? 0}', tone: 'warning')),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: SizedBox(
              height: 34,
              child: ListView(
                scrollDirection: Axis.horizontal,
                children: [
                  for (final (value, label) in _tiers) ...[
                    FilterChip2(label: label, selected: vm.severityFilter == value, onTap: () => vm.setFilter(value)),
                    const SizedBox(width: 8),
                  ],
                ],
              ),
            ),
          ),
          Expanded(
            child: vm.loading
                ? const LoadingView()
                : vm.error != null
                    ? ErrorView(message: vm.error!)
                    : vm.filtered.isEmpty
                        ? const EmptyView(icon: Icons.check_circle_outline, message: 'No alerts match this filter')
                        : RefreshIndicator(
                            onRefresh: vm.refresh,
                            child: ListView.separated(
                              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                              itemCount: vm.filtered.length,
                              separatorBuilder: (_, _) => const SizedBox(height: 10),
                              itemBuilder: (context, i) {
                                final a = vm.filtered[i];
                                return Card(
                                  child: Padding(
                                    padding: const EdgeInsets.all(14),
                                    child: Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Container(
                                          width: 36, height: 36,
                                          decoration: BoxDecoration(
                                            color: AppColors.dim(toneColor(_tierTone(a.severityTier))),
                                            borderRadius: BorderRadius.circular(10),
                                          ),
                                          child: Icon(Icons.bolt, color: toneColor(_tierTone(a.severityTier)), size: 18),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: [
                                                  Expanded(
                                                    child: Text(a.attackType.toUpperCase(), style: const TextStyle(
                                                        color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 13)),
                                                  ),
                                                  Text(DateFormat('HH:mm:ss').format(a.dateTime),
                                                      style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
                                                ],
                                              ),
                                              const SizedBox(height: 4),
                                              Text(a.description, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                                              const SizedBox(height: 8),
                                              Row(
                                                children: [
                                                  StatusBadge(label: a.meterId, tone: 'neutral'),
                                                  const SizedBox(width: 6),
                                                  StatusBadge(label: a.severityTier.toUpperCase(), tone: _tierTone(a.severityTier)),
                                                ],
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
          ),
        ],
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
