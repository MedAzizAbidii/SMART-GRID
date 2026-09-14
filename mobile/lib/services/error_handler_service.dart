import 'package:flutter/material.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';
import '../api/api_client.dart' show ApiException, SocketException, TimeoutException;

enum ErrorSeverity { critical, warning, info }

class ErrorInfo {
  final String message;
  final String? friendlyMessage;
  final String? code;
  final ErrorSeverity severity;
  final dynamic originalError;
  final StackTrace? stackTrace;
  final DateTime timestamp;

  ErrorInfo({
    required this.message,
    this.friendlyMessage,
    this.code,
    this.severity = ErrorSeverity.warning,
    this.originalError,
    this.stackTrace,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory ErrorInfo.fromException(dynamic e, {String? friendlyMessage}) {
    String message = e.toString();
    String? code;
    ErrorSeverity severity = ErrorSeverity.warning;

    if (e is SocketException) {
      message = 'Network connection error';
      code = 'NETWORK_ERROR';
      severity = ErrorSeverity.critical;
    } else if (e is TimeoutException) {
      message = 'Request timed out';
      code = 'TIMEOUT';
      severity = ErrorSeverity.warning;
    } else if (e is ApiException) {
      message = 'API error: ${e.statusCode}';
      code = 'API_${e.statusCode}';
      if (e.statusCode == 401) {
        severity = ErrorSeverity.critical;
      }
    } else if (e is FormatException) {
      message = 'Data format error';
      code = 'FORMAT_ERROR';
      severity = ErrorSeverity.warning;
    }

    return ErrorInfo(
      message: message,
      friendlyMessage: friendlyMessage,
      code: code,
      severity: severity,
      originalError: e,
    );
  }

  bool get isNetworkError => code == 'NETWORK_ERROR' || code == 'TIMEOUT';
  bool get isAuthError => code == 'API_401';
  bool get isCritical => severity == ErrorSeverity.critical;
}

class ErrorHandlerService {
  static final ErrorHandlerService _instance = ErrorHandlerService._internal();
  final List<ErrorInfo> _errorHistory = [];
  static const int _maxHistory = 50;

  factory ErrorHandlerService() => _instance;

  ErrorHandlerService._internal();

  Future<void> handle(
    dynamic error,
    StackTrace? stackTrace, {
    String? friendlyMessage,
    void Function(ErrorInfo)? onError,
  }) async {
    final errorInfo = ErrorInfo.fromException(
      error,
      friendlyMessage: friendlyMessage,
    );

    _errorHistory.add(errorInfo);
    if (_errorHistory.length > _maxHistory) {
      _errorHistory.removeAt(0);
    }

    debugPrint('${_severityEmoji(errorInfo.severity)} ${errorInfo.message}');

    // Report to Crashlytics in production
    if (!kDebugMode && errorInfo.isCritical) {
      await FirebaseCrashlytics.instance.recordError(error, stackTrace);
    }

    onError?.call(errorInfo);
  }

  String _severityEmoji(ErrorSeverity severity) {
    return switch (severity) {
      ErrorSeverity.critical => '🚨',
      ErrorSeverity.warning => '⚠️',
      ErrorSeverity.info => 'ℹ️',
    };
  }

  List<ErrorInfo> getErrorHistory() => List.unmodifiable(_errorHistory);

  void clearHistory() => _errorHistory.clear();
}

// UI helper to show error messages
class ErrorSnackBar {
  static void show(BuildContext context, ErrorInfo error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              error.friendlyMessage ?? error.message,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            if (error.code != null)
              Text(
                'Error: ${error.code}',
                style: const TextStyle(fontSize: 12),
              ),
          ],
        ),
        backgroundColor: _colorForSeverity(error.severity),
        duration: Duration(seconds: error.isCritical ? 8 : 4),
        action: SnackBarAction(
          label: 'Dismiss',
          textColor: Colors.white,
          onPressed: () {},
        ),
      ),
    );
  }

  static Color _colorForSeverity(ErrorSeverity severity) {
    return switch (severity) {
      ErrorSeverity.critical => Colors.red[800]!,
      ErrorSeverity.warning => Colors.orange[700]!,
      ErrorSeverity.info => Colors.blue[700]!,
    };
  }
}

