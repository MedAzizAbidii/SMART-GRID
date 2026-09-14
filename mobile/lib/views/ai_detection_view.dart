import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/ai_detection_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/sparkline.dart';
import '../widgets/status_card.dart';

class AiDetectionView extends StatelessWidget {
  const AiDetectionView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<AiDetectionViewModel>();
    final detector = vm.model?.detector;
    final champion = vm.model?.championMetrics;
    final latest = vm.latest;
    final scores = vm.history.map((p) => p.score).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Detection'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: StatusBadge(
                label: (detector?.loaded ?? false) ? 'Loaded' : 'Unavailable',
                tone: (detector?.loaded ?? false) ? 'success' : 'critical',
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Transformer Autoencoder ensemble · live inference via /api/detect (seq_len=${detector?.seqLen ?? 8})',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Live Detection Feed', style: TextStyle(
                            color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 14)),
                        const SizedBox(height: 4),
                        const Text('Streams real bus-1 readings every 1.5s to build a live sequence buffer',
                            style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton.icon(
                    onPressed: vm.toggleFeed,
                    icon: Icon(vm.feeding ? Icons.stop : Icons.play_arrow, size: 16),
                    label: Text(vm.feeding ? 'Stop' : 'Start'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: vm.feeding ? AppColors.critical : AppColors.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.5,
            children: [
              StatusCard(
                icon: Icons.gps_fixed,
                label: 'Anomaly Score',
                value: latest != null ? latest.anomalyScore.toStringAsFixed(5) : '—',
                tone: (latest?.isAnomaly ?? false) ? 'critical' : 'success',
              ),
              StatusCard(
                icon: Icons.speed,
                label: 'Confidence',
                value: latest != null ? '${(latest.confidence * 100).round()}%' : '—',
              ),
              StatusCard(
                icon: Icons.timer_outlined,
                label: 'Inference Time',
                value: latest != null ? '${latest.inferenceMs.toStringAsFixed(1)} ms' : '—',
                tone: 'info',
              ),
              StatusCard(
                icon: Icons.memory,
                label: 'Buffer Fill',
                value: latest != null ? '${latest.bufferFill}/${detector?.seqLen ?? 8}' : '—',
                tone: 'neutral',
              ),
            ],
          ),
          const SizedBox(height: 8),
          const SectionHeader(title: 'Reconstruction Score Timeline'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: scores.length < 2
                  ? const SizedBox(
                      height: 100,
                      child: Center(child: Text('Start the live feed to see real-time scores',
                          style: TextStyle(color: AppColors.textMuted))))
                  : Sparkline(data: scores, color: AppColors.primary, height: 100),
            ),
          ),
          const SizedBox(height: 8),
          const SectionHeader(title: 'Decision Panel'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: latest == null || latest.isBuffering
                  ? const Text('Buffering readings — the model needs a full sequence before it can decide.',
                      style: TextStyle(color: AppColors.textMuted))
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        StatusBadge(
                          label: latest.isAnomaly ? 'Anomaly — ${latest.attackType}' : 'Normal behavior',
                          tone: latest.isAnomaly ? 'critical' : 'success',
                        ),
                        const SizedBox(height: 10),
                        Text(
                          latest.isAnomaly
                              ? 'The reconstruction error (${latest.anomalyScore.toStringAsFixed(5)}) exceeds the adaptive threshold (${latest.threshold.toStringAsFixed(5)}), classified as ${latest.attackType} with ${(latest.confidence * 100).round()}% confidence.'
                              : 'The reconstruction error (${latest.anomalyScore.toStringAsFixed(5)}) is within the adaptive threshold (${latest.threshold.toStringAsFixed(5)}) — no deviation detected.',
                          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13, height: 1.4),
                        ),
                        if (latest.topFeatures.isNotEmpty) ...[
                          const SizedBox(height: 14),
                          const Text('Top contributing features',
                              style: TextStyle(color: AppColors.textMuted, fontSize: 11, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 8),
                          for (final f in latest.topFeatures.take(3)) ...[
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(child: Text(f.feature, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12))),
                                      Text('${(f.contribution * 100).toStringAsFixed(1)}%', style: const TextStyle(color: AppColors.textPrimary, fontSize: 12, fontWeight: FontWeight.w600)),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  ProgressBar(value: f.contribution * 100),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 8),
          SectionHeader(title: 'Champion Model — ${vm.model?.championVersion ?? "—"}'),
          if (champion == null || !champion.hasData)
            const Card(child: Padding(padding: EdgeInsets.all(20), child: Text('Model registry unavailable', style: TextStyle(color: AppColors.textMuted))))
          else
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  children: [
                    _metricRow('Accuracy', champion.accuracy),
                    _metricRow('Precision', champion.precision),
                    _metricRow('Recall', champion.recall),
                    _metricRow('ROC-AUC', champion.rocAuc),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _metricRow(String label, double? value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
            Text(value != null ? '${(value * 100).toStringAsFixed(2)}%' : '—',
                style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 13)),
          ],
        ),
      );
}
