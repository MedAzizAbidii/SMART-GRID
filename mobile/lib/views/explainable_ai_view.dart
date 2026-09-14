import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/detection.dart';
import '../theme/app_theme.dart';
import '../viewmodels/explainable_ai_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';

const _tabs = [
  (XaiTab.features, 'Feature Importance'),
  (XaiTab.gradients, 'Integrated Gradients'),
  (XaiTab.attention, 'Attention Map'),
  (XaiTab.shap, 'SHAP'),
  (XaiTab.breakdown, 'Breakdown'),
];

class ExplainableAiView extends StatelessWidget {
  const ExplainableAiView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<ExplainableAiViewModel>();

    return Scaffold(
      appBar: AppBar(title: const Text('Explainable AI')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Real-time explanations (WHERE = attention, WHY = integrated gradients), exactly as computed by ingest() in production.',
              style: TextStyle(color: AppColors.textMuted, fontSize: 12, height: 1.4)),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  const Expanded(
                    child: Text('Runs 9 consecutive readings from live bus 1, then explains the final prediction.',
                        style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton.icon(
                    onPressed: vm.running ? null : vm.runExplanation,
                    icon: vm.running
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.play_arrow, size: 16),
                    label: Text(vm.running ? 'Running' : 'Run'),
                  ),
                ],
              ),
            ),
          ),
          if (vm.error != null) ...[
            const SizedBox(height: 10),
            Text(vm.error!, style: const TextStyle(color: AppColors.critical, fontSize: 12)),
          ],
          const SizedBox(height: 14),
          SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                for (final (value, label) in _tabs) ...[
                  FilterChip2(label: label, selected: vm.tab == value, onTap: () => vm.setTab(value)),
                  const SizedBox(width: 8),
                ],
              ],
            ),
          ),
          const SizedBox(height: 14),
          if (!vm.hasResult)
            const Card(child: Padding(padding: EdgeInsets.all(24),
                child: Center(child: Text('Run an explanation above to see live results', style: TextStyle(color: AppColors.textMuted)))))
          else
            _buildTabContent(vm),
        ],
      ),
    );
  }

  Widget _buildTabContent(ExplainableAiViewModel vm) {
    final result = vm.result!;
    switch (vm.tab) {
      case XaiTab.features:
        return _featureBars(result.topFeatures, 'Top Feature Contributions');
      case XaiTab.gradients:
        return Column(children: [
          _featureBars(result.topFeatures, 'Integrated Gradients Attribution (production XAI method)'),
          const SizedBox(height: 10),
          const Text('Computed via 20-step gradient interpolation against a zero baseline — the method actually used in the real-time path, since SHAP is too slow for it.',
              style: TextStyle(color: AppColors.textMuted, fontSize: 11, height: 1.4)),
        ]);
      case XaiTab.attention:
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Critical timestep (highest attention weight) in the 8-reading sequence:',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                const SizedBox(height: 10),
                Row(
                  children: List.generate(8, (i) {
                    final isCritical = i == result.criticalTimestep;
                    return Expanded(
                      child: Container(
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        height: 44,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: isCritical ? AppColors.primary : AppColors.card,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: isCritical ? AppColors.primary : AppColors.border),
                        ),
                        child: Text('t-${7 - i}', style: TextStyle(
                            color: isCritical ? Colors.white : AppColors.textMuted,
                            fontSize: 11, fontWeight: FontWeight.w700)),
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 10),
                const Text('Measured caveat: attention entropy on this model is ~0.96/1.0 — near-uniform — so this highlighted step is a weak signal, not a confident localization.',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 11, height: 1.4)),
              ],
            ),
          ),
        );
      case XaiTab.shap:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SampleDataTag(),
            const SizedBox(height: 10),
            const Text('SHAP is implemented but only run offline — it is too slow for the real-time detection path. No live endpoint exists to compute it on demand, so these are illustrative sample values, not a real call.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 12, height: 1.4)),
            const SizedBox(height: 10),
            _featureBars(ExplainableAiViewModel.sampleShapFeatures, 'Sample SHAP values (illustrative)'),
          ],
        );
      case XaiTab.breakdown:
        return Row(
          children: [
            Expanded(child: _breakdownStat('v2 (recall)', result.v2Score, result.v2Alarm)),
            const SizedBox(width: 10),
            Expanded(child: _breakdownStat('v3 (precision)', result.v3Score, result.v3Alarm)),
            const SizedBox(width: 10),
            Expanded(child: _breakdownStat('Ensemble', result.confidence, result.isAnomaly, isConfidence: true, label2: result.confidenceLabel)),
          ],
        );
    }
  }

  Widget _featureBars(List<FeatureContribution> features, String title) {
    if (features.isEmpty) {
      return const Card(child: Padding(padding: EdgeInsets.all(20), child: Text('No feature data', style: TextStyle(color: AppColors.textMuted))));
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(color: AppColors.textMuted, fontSize: 11, fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            for (final f in features) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(child: Text(f.feature, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12))),
                        Text('${(f.contribution * 100).toStringAsFixed(1)}%', style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 12)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    ProgressBar(value: f.contribution * 100),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _breakdownStat(String label, double? score, bool? alarm, {bool isConfidence = false, String? label2}) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
            const SizedBox(height: 6),
            Text(
              isConfidence ? '${((score ?? 0) * 100).round()}%' : (score?.toStringAsFixed(5) ?? '—'),
              style: const TextStyle(color: AppColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            StatusBadge(label: label2 ?? ((alarm ?? false) ? 'Alarm' : 'Normal'), tone: (alarm ?? false) ? 'critical' : 'success'),
          ],
        ),
      ),
    );
  }
}
