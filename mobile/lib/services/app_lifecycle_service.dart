import 'package:flutter/material.dart';
import 'dart:async';

enum AppForegroundState { resumed, paused, detached }

class AppLifecycleService extends WidgetsBindingObserver {
  static final AppLifecycleService _instance = AppLifecycleService._internal();

  final StreamController<AppForegroundState> _lifecycleStream = StreamController.broadcast();
  AppForegroundState _currentState = AppForegroundState.resumed;
  DateTime? _lastPausedTime;

  factory AppLifecycleService() => _instance;

  AppLifecycleService._internal();

  Stream<AppForegroundState> get lifecycleStream => _lifecycleStream.stream;
  AppForegroundState get currentState => _currentState;
  bool get isAppInBackground => _currentState == AppForegroundState.paused;
  DateTime? get lastPausedTime => _lastPausedTime;

  void initialize() {
    WidgetsBinding.instance.addObserver(this);
    debugPrint('✓ App lifecycle observer registered');
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _currentState = AppForegroundState.resumed;
        _lifecycleStream.add(AppForegroundState.resumed);
        debugPrint('▶️ App resumed');

      case AppLifecycleState.paused:
        _currentState = AppForegroundState.paused;
        _lastPausedTime = DateTime.now();
        _lifecycleStream.add(AppForegroundState.paused);
        debugPrint('⏸️ App paused');

      case AppLifecycleState.detached:
        _currentState = AppForegroundState.detached;
        _lifecycleStream.add(AppForegroundState.detached);
        debugPrint('❌ App detached');

      case AppLifecycleState.inactive:
        debugPrint('⏳ App inactive');

      case AppLifecycleState.hidden:
        debugPrint('🙈 App hidden');
    }
  }

  Duration get timeInBackground {
    if (_lastPausedTime == null) return Duration.zero;
    if (_currentState != AppForegroundState.resumed) return Duration.zero;
    return DateTime.now().difference(_lastPausedTime!);
  }

  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _lifecycleStream.close();
    debugPrint('✓ App lifecycle observer removed');
  }
}
