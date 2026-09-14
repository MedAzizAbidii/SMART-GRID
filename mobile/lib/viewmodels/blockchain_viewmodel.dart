import '../models/blockchain.dart';
import '../repositories/smart_grid_repository.dart';
import 'polling_viewmodel.dart';

/// Mirrors the web Blockchain.jsx page: local PoA ledger status plus the
/// optional real on-chain (Sepolia) bridge status — disabled-by-default is
/// a normal, honestly-labeled state, not an error.
class BlockchainViewModel extends PollingViewModel {
  final SmartGridRepository repo;
  BlockchainViewModel(this.repo);

  @override
  Duration get interval => const Duration(seconds: 8);

  BlockchainStatus? local;
  OnchainStatus? onchain;
  bool anchoring = false;
  String? anchorMessage;

  Future<void> triggerAnchor() async {
    anchoring = true;
    anchorMessage = null;
    notifyListeners();
    try {
      final result = await repo.triggerOnchainAnchor();
      anchorMessage = result['anchored'] == true
          ? 'Anchored PoA block ${result['poa_block_index']} on-chain'
          : (result['reason']?.toString() ?? 'Nothing new to anchor');
    } catch (e) {
      anchorMessage = 'Anchor failed: ${e.toString()}';
    } finally {
      anchoring = false;
      notifyListeners();
    }
  }

  @override
  Future<void> fetch() async {
    final results = await Future.wait([repo.getBlockchainStatus(), repo.getOnchainStatus()]);
    local = results[0] as BlockchainStatus;
    onchain = results[1] as OnchainStatus;
  }
}
