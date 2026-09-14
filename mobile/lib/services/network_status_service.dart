import 'package:flutter/material.dart';
import 'dart:async';

enum NetworkStatus { online, offline, unstable }

class NetworkStatusService {
  static final NetworkStatusService _instance = NetworkStatusService._internal();
  final StreamController<NetworkStatus> _statusStream = StreamController.broadcast();
  NetworkStatus _currentStatus = NetworkStatus.online;
  int _failureCount = 0;
  static const int _failureThreshold = 3;

  factory NetworkStatusService() => _instance;

  NetworkStatusService._internal();

  Stream<NetworkStatus> get statusStream => _statusStream.stream;
  NetworkStatus get currentStatus => _currentStatus;
  bool get isOnline => _currentStatus == NetworkStatus.online;
  bool get isOffline => _currentStatus == NetworkStatus.offline;

  void recordSuccess() {
    _failureCount = 0;
    if (_currentStatus != NetworkStatus.online) {
      _updateStatus(NetworkStatus.online);
    }
  }

  void recordFailure() {
    _failureCount++;
    if (_failureCount >= _failureThreshold && _currentStatus == NetworkStatus.online) {
      _updateStatus(NetworkStatus.unstable);
    } else if (_failureCount > _failureThreshold * 2 && _currentStatus != NetworkStatus.offline) {
      _updateStatus(NetworkStatus.offline);
    }
  }

  void setOffline() {
    _updateStatus(NetworkStatus.offline);
  }

  void setOnline() {
    _failureCount = 0;
    _updateStatus(NetworkStatus.online);
  }

  void _updateStatus(NetworkStatus newStatus) {
    if (_currentStatus != newStatus) {
      _currentStatus = newStatus;
      _statusStream.add(newStatus);
      debugPrint('📡 Network status: $_currentStatus');
    }
  }

  void dispose() {
    _statusStream.close();
  }
}
