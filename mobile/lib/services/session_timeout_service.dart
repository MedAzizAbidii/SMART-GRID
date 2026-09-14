import 'package:flutter/material.dart';
import 'dart:async';

class SessionTimeoutService {
  static final SessionTimeoutService _instance = SessionTimeoutService._internal();

  Timer? _inactivityTimer;
  Timer? _warningTimer;
  final Duration inactivityTimeout = const Duration(minutes: 15);
  final Duration warningThreshold = const Duration(minutes: 14);

  DateTime? _lastActivityTime;
  bool _isTimedOut = false;

  final StreamController<SessionEvent> _eventStream = StreamController.broadcast();

  factory SessionTimeoutService() => _instance;

  SessionTimeoutService._internal();

  Stream<SessionEvent> get eventStream => _eventStream.stream;
  bool get isTimedOut => _isTimedOut;
  DateTime? get lastActivityTime => _lastActivityTime;

  void startMonitoring() {
    _lastActivityTime = DateTime.now();
    _resetInactivityTimer();
    debugPrint('✓ Session monitoring started');
  }

  void recordActivity() {
    _lastActivityTime = DateTime.now();
    _isTimedOut = false;
    _resetInactivityTimer();
  }

  void _resetInactivityTimer() {
    _inactivityTimer?.cancel();
    _warningTimer?.cancel();

    _warningTimer = Timer(warningThreshold, () {
      _eventStream.add(SessionEvent.warningAboutToExpire);
      debugPrint('⚠️ Session expiring in 1 minute');
    });

    _inactivityTimer = Timer(inactivityTimeout, () {
      _isTimedOut = true;
      _eventStream.add(SessionEvent.expired);
      debugPrint('⏱️ Session expired');
    });
  }

  void extendSession() {
    recordActivity();
    _eventStream.add(SessionEvent.extended);
    debugPrint('✓ Session extended');
  }

  void logout() {
    _inactivityTimer?.cancel();
    _warningTimer?.cancel();
    _isTimedOut = false;
    _eventStream.add(SessionEvent.loggedOut);
    debugPrint('✓ Session ended');
  }

  Duration get remainingTime {
    if (_lastActivityTime == null) return Duration.zero;
    final elapsed = DateTime.now().difference(_lastActivityTime!);
    final remaining = inactivityTimeout - elapsed;
    return remaining.isNegative ? Duration.zero : remaining;
  }

  void dispose() {
    _inactivityTimer?.cancel();
    _warningTimer?.cancel();
    _eventStream.close();
  }
}

enum SessionEvent {
  warningAboutToExpire,
  expired,
  extended,
  loggedOut,
}
