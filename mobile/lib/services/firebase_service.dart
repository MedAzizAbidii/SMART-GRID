import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import 'package:shared_preferences/shared_preferences.dart';

class PushNotificationPayload {
  final String title;
  final String body;
  final String type;
  final Map<String, dynamic> data;
  final DateTime timestamp;

  PushNotificationPayload({
    required this.title,
    required this.body,
    required this.type,
    required this.data,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory PushNotificationPayload.fromRemoteMessage(RemoteMessage message) {
    return PushNotificationPayload(
      title: message.notification?.title ?? 'Alert',
      body: message.notification?.body ?? '',
      type: message.data['type'] ?? 'alert',
      data: message.data,
    );
  }

  Map<String, dynamic> toJson() => {
    'title': title,
    'body': body,
    'type': type,
    'data': data,
    'timestamp': timestamp.toIso8601String(),
  };
}

class FirebaseService {
  static final FirebaseService _instance = FirebaseService._internal();
  static FirebaseMessaging? _messaging;
  static FirebaseAnalytics? _analytics;
  static FirebaseCrashlytics? _crashlytics;

  final StreamController<PushNotificationPayload> _notificationStream = StreamController.broadcast();
  final StreamController<bool> _connectionStream = StreamController.broadcast();

  factory FirebaseService() {
    return _instance;
  }

  FirebaseService._internal();

  Stream<PushNotificationPayload> get notificationStream => _notificationStream.stream;
  Stream<bool> get connectionStream => _connectionStream.stream;

  static Future<void> initialize() async {
    try {
      // Skip Firebase on web (not supported for demo)
      if (kIsWeb) {
        debugPrint('⚠️ Firebase skipped on web (demo mode)');
        return;
      }

      await Firebase.initializeApp();
      _messaging = FirebaseMessaging.instance;
      _analytics = FirebaseAnalytics.instance;
      _crashlytics = FirebaseCrashlytics.instance;

      // Request permissions (iOS requires explicit request)
      final settings = await _messaging!.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );

      if (settings.authorizationStatus == AuthorizationStatus.authorized) {
        debugPrint('✓ Firebase Messaging authorized');
      }

      // Get FCM token and persist it for backend registration
      final token = await _messaging!.getToken();
      if (token != null) {
        debugPrint('✓ FCM Token: $token');
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('fcm_token', token);
      }

      // Handle foreground messages with sound and badge
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

      // Handle background messages
      FirebaseMessaging.onMessageOpenedApp.listen(_handleMessageOpenedApp);

      // Handle notifications when app is terminated
      final initialMessage = await _messaging!.getInitialMessage();
      if (initialMessage != null) {
        _handleMessageOpenedApp(initialMessage);
      }

      // Listen for token refresh
      _messaging!.onTokenRefresh.listen((newToken) {
        debugPrint('✓ FCM Token refreshed: $newToken');
        SharedPreferences.getInstance().then((prefs) {
          prefs.setString('fcm_token', newToken);
        });
      });

      // Enable crash reporting in release builds
      if (!kDebugMode) {
        FlutterError.onError = _crashlytics!.recordFlutterError;
        PlatformDispatcher.instance.onError = (error, stack) {
          _crashlytics!.recordError(error, stack);
          return true;
        };
      }

      // Subscribe to alert topics by default
      await subscribeToTopic('alerts');
      await subscribeToTopic('grid_operator');

      debugPrint('✓ Firebase fully initialized with push notifications');
    } catch (e) {
      debugPrint('Firebase initialization error: $e');
      rethrow;
    }
  }

  static void _handleForegroundMessage(RemoteMessage message) {
    final payload = PushNotificationPayload.fromRemoteMessage(message);
    debugPrint('📬 Foreground notification: ${payload.title}');
    _instance._notificationStream.add(payload);

    _analytics?.logEvent(name: 'notification_received', parameters: {
      'title': payload.title,
      'type': payload.type,
    });
  }

  static void _handleMessageOpenedApp(RemoteMessage message) {
    final payload = PushNotificationPayload.fromRemoteMessage(message);
    debugPrint('🔔 User tapped notification: ${payload.title}');
    _instance._notificationStream.add(payload);

    _analytics?.logEvent(name: 'notification_tapped', parameters: {
      'title': payload.title,
      'type': payload.type,
    });
  }

  static Future<String?> getFCMToken() async {
    try {
      return await _messaging?.getToken();
    } catch (e) {
      debugPrint('Error getting FCM token: $e');
      return null;
    }
  }

  static Future<void> subscribeToTopic(String topic) async {
    try {
      await _messaging?.subscribeToTopic(topic);
      debugPrint('✓ Subscribed to topic: $topic');
    } catch (e) {
      debugPrint('Error subscribing to topic: $e');
    }
  }

  static Future<void> unsubscribeFromTopic(String topic) async {
    try {
      await _messaging?.unsubscribeFromTopic(topic);
      debugPrint('✓ Unsubscribed from topic: $topic');
    } catch (e) {
      debugPrint('Error unsubscribing from topic: $e');
    }
  }

  static void logEvent(String name, {Map<String, Object>? parameters}) {
    _analytics?.logEvent(name: name, parameters: parameters);
  }

  static void logError(dynamic error, {StackTrace? stackTrace}) {
    if (!kDebugMode) {
      _crashlytics?.recordError(error, stackTrace ?? StackTrace.current);
    } else {
      debugPrint('❌ Error: $error\n$stackTrace');
    }
  }

  void dispose() {
    _notificationStream.close();
    _connectionStream.close();
  }
}
