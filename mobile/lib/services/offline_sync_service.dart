import 'package:flutter/foundation.dart';
import 'dart:async';

class OfflineSyncRequest {
  final String id;
  final String endpoint;
  final String method;
  final Map<String, dynamic> body;
  final DateTime createdAt;
  bool synced;

  OfflineSyncRequest({
    required this.id,
    required this.endpoint,
    required this.method,
    required this.body,
    DateTime? createdAt,
    this.synced = false,
  }) : createdAt = createdAt ?? DateTime.now();
}

class OfflineSyncService {
  static final OfflineSyncService _instance = OfflineSyncService._internal();
  final List<OfflineSyncRequest> _pendingSyncQueue = [];
  Timer? _syncTimer;
  bool _isSyncing = false;
  Future<dynamic> Function(String, String, Map)? _syncHandler;

  final StreamController<SyncEvent> _syncStream = StreamController.broadcast();

  factory OfflineSyncService() => _instance;

  OfflineSyncService._internal();

  Stream<SyncEvent> get syncStream => _syncStream.stream;
  List<OfflineSyncRequest> get pendingRequests => List.unmodifiable(_pendingSyncQueue);
  int get pendingCount => _pendingSyncQueue.length;
  bool get isSyncing => _isSyncing;

  void setSyncHandler(Future<dynamic> Function(String, String, Map) handler) {
    _syncHandler = handler;
  }

  void startAutoSync({Duration interval = const Duration(seconds: 30)}) {
    _syncTimer?.cancel();
    _syncTimer = Timer.periodic(interval, (_) => sync());
    debugPrint('✓ Auto-sync started (interval: ${interval.inSeconds}s)');
  }

  void queueRequest({
    required String endpoint,
    required String method,
    required Map<String, dynamic> body,
  }) {
    final request = OfflineSyncRequest(
      id: '${DateTime.now().millisecondsSinceEpoch}',
      endpoint: endpoint,
      method: method,
      body: body,
    );

    _pendingSyncQueue.add(request);
    _syncStream.add(SyncEvent.requestQueued);
    debugPrint('📤 Queued offline request: $endpoint (${_pendingSyncQueue.length} pending)');
  }

  Future<void> sync() async {
    if (_syncHandler == null) return;

    if (_isSyncing || _pendingSyncQueue.isEmpty) return;

    _isSyncing = true;
    _syncStream.add(SyncEvent.syncStarted);
    debugPrint('🔄 Starting sync (${_pendingSyncQueue.length} requests)...');

    int syncedCount = 0;
    int failedCount = 0;

    for (final request in List.from(_pendingSyncQueue)) {
      try {
        await _syncHandler!(request.endpoint, request.method, request.body);
        request.synced = true;
        _pendingSyncQueue.remove(request);
        syncedCount++;
        debugPrint('✓ Synced: ${request.endpoint}');
      } catch (e) {
        failedCount++;
        debugPrint('✗ Failed to sync ${request.endpoint}: $e');
      }
    }

    _isSyncing = false;
    _syncStream.add(SyncEvent.syncCompleted);
    debugPrint('✓ Sync complete: $syncedCount synced, $failedCount failed');
  }

  Future<void> clearQueue() async {
    _pendingSyncQueue.clear();
    _syncStream.add(SyncEvent.queueCleared);
    debugPrint('🗑️ Sync queue cleared');
  }

  void stopAutoSync() {
    _syncTimer?.cancel();
    debugPrint('✓ Auto-sync stopped');
  }

  void dispose() {
    _syncTimer?.cancel();
    _syncStream.close();
    debugPrint('✓ Offline sync service disposed');
  }
}

enum SyncEvent {
  requestQueued,
  syncStarted,
  syncCompleted,
  queueCleared,
}
