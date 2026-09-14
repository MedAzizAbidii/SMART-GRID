/// Mirrors GET /api/blockchain/status (local PoA ledger).
class BlockchainStatus {
  final bool available;
  final bool valid;
  final List<String> errors;
  final int blocks;
  final List<String> authorities;

  BlockchainStatus({
    required this.available,
    required this.valid,
    required this.errors,
    required this.blocks,
    required this.authorities,
  });

  factory BlockchainStatus.fromJson(Map<String, dynamic> json) => BlockchainStatus(
        available: json['available'] == true,
        valid: json['valid'] == true,
        errors: (json['errors'] as List?)?.map((e) => e.toString()).toList() ?? [],
        blocks: (json['blocks'] as num?)?.toInt() ?? 0,
        authorities: (json['authorities'] as List?)?.map((e) => e.toString()).toList() ?? [],
      );
}

/// Mirrors GET /api/blockchain/onchain/status (real Ethereum/Sepolia bridge —
/// off by default; `enabled: false` is a normal, expected state).
class OnchainStatus {
  final bool enabled;
  final String? reason;
  final String? network;
  final int? chainId;
  final String? account;
  final double? balanceEth;
  final Map<String, String> contracts;
  final int anomalyRecordCount;
  final int anchorCount;

  OnchainStatus({
    required this.enabled,
    this.reason,
    this.network,
    this.chainId,
    this.account,
    this.balanceEth,
    this.contracts = const {},
    this.anomalyRecordCount = 0,
    this.anchorCount = 0,
  });

  factory OnchainStatus.fromJson(Map<String, dynamic> json) => OnchainStatus(
        enabled: json['enabled'] == true,
        reason: json['reason'] as String?,
        network: json['network'] as String?,
        chainId: (json['chain_id'] as num?)?.toInt(),
        account: json['account'] as String?,
        balanceEth: (json['balance_eth'] as num?)?.toDouble(),
        contracts: (json['contracts'] as Map?)?.map((k, v) => MapEntry(k.toString(), v.toString())) ?? {},
        anomalyRecordCount: (json['anomaly_record_count'] as num?)?.toInt() ?? 0,
        anchorCount: (json['anchor_count'] as num?)?.toInt() ?? 0,
      );
}
