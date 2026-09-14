import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:web3dart/web3dart.dart';

class BlockchainService {
  static final BlockchainService _instance = BlockchainService._internal();
  late Web3Client _client;
  late String _contractAddress;
  late String _privateKey;

  factory BlockchainService() {
    return _instance;
  }

  BlockchainService._internal();

  Future<void> initialize({
    required String rpcUrl,
    required String contractAddress,
    required String privateKey,
  }) async {
    try {
      _contractAddress = contractAddress;
      _privateKey = privateKey;
      _client = Web3Client(rpcUrl, http.Client());

      // Verify connection
      final chainId = await _client.getChainId();
      debugPrint('✓ Blockchain connected (Chain ID: $chainId)');
    } catch (e) {
      debugPrint('Blockchain initialization error: $e');
      rethrow;
    }
  }

  Future<String> recordAnomaly({
    required String meterId,
    required String attackType,
    required int confidence,
    required String offChainHash,
  }) async {
    try {
      // Contract ABI would be defined separately - simplified for now
      // This requires loading AnomalyRegistry ABI
      // final credentials = EthPrivateKey.fromHex(_privateKey);

      debugPrint('Recording anomaly: $meterId - $attackType');
      // Transaction hash would be returned from actual contract call
      return 'tx_hash_placeholder';
    } catch (e) {
      debugPrint('Error recording anomaly: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getAnomalyRecord(int recordId) async {
    try {
      // Query contract for anomaly record
      debugPrint('Fetching anomaly record: $recordId');
      return {'id': recordId, 'status': 'pending'};
    } catch (e) {
      debugPrint('Error fetching anomaly record: $e');
      return {};
    }
  }

  Future<int> getRecordCount() async {
    try {
      // Query contract for total records
      return 0;
    } catch (e) {
      debugPrint('Error getting record count: $e');
      return 0;
    }
  }

  Future<bool> verifyTransaction(String txHash) async {
    try {
      final receipt = await _client.getTransactionReceipt(txHash);
      return receipt != null && receipt.status == true;
    } catch (e) {
      debugPrint('Error verifying transaction: $e');
      return false;
    }
  }

  Future<String> getContractBalance() async {
    try {
      final balance = await _client.getBalance(EthereumAddress.fromHex(_contractAddress));
      return balance.getInWei.toString();
    } catch (e) {
      debugPrint('Error getting contract balance: $e');
      return '0';
    }
  }

  Future<void> disconnect() async {
    _client.dispose();
    debugPrint('✓ Blockchain disconnected');
  }
}
