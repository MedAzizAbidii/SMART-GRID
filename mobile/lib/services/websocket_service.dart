import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _messageController = StreamController.broadcast();
  late String _url;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;
  static const Duration _reconnectDelay = Duration(seconds: 3);

  factory WebSocketService() {
    return _instance;
  }

  WebSocketService._internal();

  Stream<Map<String, dynamic>> get messages => _messageController.stream;

  Future<void> connect(String url, {String? token}) async {
    try {
      _url = url;
      _channel = WebSocketChannel.connect(Uri.parse(url));

      _reconnectAttempts = 0;

      _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message);
            _messageController.add(data);
          } catch (e) {
            debugPrint('WebSocket message parse error: $e');
          }
        },
        onError: (error) {
          debugPrint('WebSocket error: $error');
          _attemptReconnect();
        },
        onDone: () {
          debugPrint('WebSocket connection closed');
          _attemptReconnect();
        },
      );

      debugPrint('✓ WebSocket connected to $url');
    } catch (e) {
      debugPrint('WebSocket connection error: $e');
      _attemptReconnect();
    }
  }

  void _attemptReconnect() {
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectAttempts++;
      _reconnectTimer?.cancel();
      _reconnectTimer = Timer(_reconnectDelay, () {
        debugPrint('Reconnecting WebSocket (attempt $_reconnectAttempts)...');
        connect(_url);
      });
    } else {
      debugPrint('Max reconnection attempts reached');
      unawaited(disconnect());
    }
  }

  void send(String type, {Map<String, dynamic>? data}) {
    try {
      if (_channel == null || _channel!.closeCode != null) {
        debugPrint('WebSocket not connected');
        return;
      }
      final message = {'type': type, ...?data};
      _channel!.sink.add(jsonEncode(message));
    } catch (e) {
      debugPrint('WebSocket send error: $e');
    }
  }

  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    try {
      await _channel?.sink.close();
      _channel = null;
      debugPrint('✓ WebSocket disconnected');
    } catch (e) {
      debugPrint('WebSocket disconnect error: $e');
    }
  }

  void dispose() {
    _reconnectTimer?.cancel();
    disconnect();
    _messageController.close();
  }

  bool get isConnected => _channel != null && _channel!.closeCode == null;
}
