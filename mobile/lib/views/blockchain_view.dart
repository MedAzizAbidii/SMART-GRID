import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../viewmodels/blockchain_viewmodel.dart';
import '../widgets/common.dart';
import '../widgets/status_card.dart';

class BlockchainView extends StatelessWidget {
  const BlockchainView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<BlockchainViewModel>();
    final local = vm.local;
    final onchain = vm.onchain;

    return Scaffold(
      appBar: AppBar(title: const Text('Blockchain Explorer')),
      body: vm.loading
          ? const LoadingView()
          : vm.error != null
              ? ErrorView(message: vm.error!)
              : RefreshIndicator(
                  onRefresh: vm.refresh,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      const SectionHeader(title: 'Local PoA Ledger'),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            children: [
                              _row('Total blocks', '${local?.blocks ?? "—"}'),
                              Padding(
                                padding: const EdgeInsets.symmetric(vertical: 5),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    const Text('Integrity', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                                    StatusBadge(
                                      label: (local?.valid ?? false) ? 'Verified' : 'Issues found',
                                      tone: (local?.valid ?? false) ? 'success' : 'critical',
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 8),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: Wrap(
                                  spacing: 6, runSpacing: 6,
                                  children: (local?.authorities ?? []).map((a) => StatusBadge(label: a, tone: 'info')).toList(),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const SectionHeader(title: 'On-Chain Anchor (Sepolia)'),
                      if (onchain == null || !onchain.enabled)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              children: [
                                const Icon(Icons.link_off, color: AppColors.textMuted, size: 32),
                                const SizedBox(height: 10),
                                Text(
                                  onchain?.reason ?? 'On-chain anchoring is disabled by default.',
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        )
                      else
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              children: [
                                _row('Network', onchain.network ?? '—'),
                                _row('PoA blocks anchored', '${onchain.anchorCount}'),
                                _row('Anomalies recorded on-chain', '${onchain.anomalyRecordCount}'),
                                _row('Wallet balance', '${onchain.balanceEth?.toStringAsFixed(4) ?? "—"} ETH'),
                                const SizedBox(height: 10),
                                SizedBox(
                                  width: double.infinity,
                                  child: ElevatedButton(
                                    onPressed: vm.anchoring ? null : vm.triggerAnchor,
                                    child: vm.anchoring
                                        ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                        : const Text('Anchor latest block now'),
                                  ),
                                ),
                                if (vm.anchorMessage != null) ...[
                                  const SizedBox(height: 8),
                                  Text(vm.anchorMessage!, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                ],
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
            Text(value, style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 13)),
          ],
        ),
      );
}
