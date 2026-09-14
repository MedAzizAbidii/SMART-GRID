import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../services/cache_service.dart';

/// Every method here hits a REAL, verified endpoint on api_server.py — the
/// exact same backend the web dashboard (frontend/src/api/client.js) talks
/// to. Nothing here is mocked.
///
/// Base URL: on Windows desktop (our fast dev-loop target) and on an
/// Android device reached via `adb reverse tcp:8000 tcp:8000`, the backend
/// is reachable at localhost:8000 either way — so one constant covers both
/// without per-platform branching. Override at build time for LAN/device
/// testing with `--dart-define=API_BASE_URL=...` pointed at the host's LAN IP.
class ApiClient {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  final http.Client _client;
  final CacheService _cache;
  String? _token;
  static const int _maxRetries = 3;
  static const Duration _retryDelay = Duration(milliseconds: 500);

  ApiClient({http.Client? client, CacheService? cache})
      : _client = client ?? http.Client(),
        _cache = cache ?? CacheService();

  void setToken(String? token) => _token = token;

  Map<String, String> get _authHeaders =>
      _token == null ? {} : {'Authorization': 'Bearer $_token'};

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  Future<dynamic> _retryableGet(String path, {int retries = 0}) async {
    try {
      final res = await _client
          .get(_u(path), headers: _authHeaders)
          .timeout(const Duration(seconds: 10));
      return _decode(res);
    } catch (e) {
      if (retries < _maxRetries) {
        await Future.delayed(_retryDelay * (retries + 1));
        return _retryableGet(path, retries: retries + 1);
      }
      // Return cached data on final failure (skip on web where SQLite unavailable)
      if (!kIsWeb) {
        try {
          final cached = await _cache.getCache(path);
          if (cached != null) {
            debugPrint('⚠️ Using cached data for $path (offline mode)');
            return cached;
          }
        } catch (_) {
          // Cache not available, fall through to error
        }
      }
      rethrow;
    }
  }

  Future<dynamic> _get(String path) async {
    try {
      return await _retryableGet(path);
    } catch (e) {
      debugPrint('❌ Failed to fetch $path: $e');
      rethrow;
    }
  }

  Future<dynamic> _postJson(String path, Map<String, dynamic> body) async {
    try {
      final res = await _client
          .post(_u(path), headers: {..._authHeaders, 'Content-Type': 'application/json'}, body: jsonEncode(body))
          .timeout(const Duration(seconds: 15));
      final result = _decode(res);
      if (!kIsWeb) {
        try {
          await _cache.setCache(path, result, ttl: const Duration(minutes: 5));
        } catch (_) {
          // Cache not available on web, ignore
        }
      }
      return result;
    } catch (e) {
      debugPrint('❌ Failed to POST $path: $e');
      rethrow;
    }
  }

  Future<dynamic> _patchJson(String path, Map<String, dynamic> body) async {
    try {
      final res = await _client
          .patch(_u(path), headers: {..._authHeaders, 'Content-Type': 'application/json'}, body: jsonEncode(body))
          .timeout(const Duration(seconds: 10));
      return _decode(res);
    } catch (e) {
      debugPrint('❌ Failed to PATCH $path: $e');
      rethrow;
    }
  }

  Future<void> _delete(String path) async {
    final res = await _client.delete(_u(path), headers: _authHeaders).timeout(const Duration(seconds: 10));
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(res.statusCode, res.body);
    }
  }

  dynamic _decode(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.body.isEmpty ? null : jsonDecode(res.body);
    }
    throw ApiException(res.statusCode, res.body);
  }

  // ── Auth ──────────────────────────────────────────────────────────────
  /// /api/auth/login expects x-www-form-urlencoded (FastAPI's
  /// OAuth2PasswordRequestForm) — http.post with a `Map` body of strings
  /// sends exactly that content type by default.
  Future<Map<String, dynamic>> login(String username, String password) async {
    final res = await _client.post(
      _u('/api/auth/login'),
      body: {'username': username, 'password': password},
    ).timeout(const Duration(seconds: 10));
    return _decode(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> whoAmI() async =>
      (await _get('/api/auth/me')) as Map<String, dynamic>;

  Future<void> changePassword(String currentPassword, String newPassword) async {
    await _postJson('/api/auth/change-password', {
      'current_password': currentPassword,
      'new_password': newPassword,
    });
  }

  // ── User management (administrator only) ───────────────────────────────
  Future<List<dynamic>> listUsers() async => (await _get('/api/auth/users')) as List<dynamic>;

  Future<Map<String, dynamic>> createUser(
      String username, String password, String role, String fullName) async {
    return (await _postJson('/api/auth/users', {
      'username': username,
      'password': password,
      'role': role,
      'full_name': fullName,
    })) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateUserRole(String username, String role) async {
    return (await _patchJson('/api/auth/users/$username', {'role': role})) as Map<String, dynamic>;
  }

  Future<void> deleteUser(String username) async => _delete('/api/auth/users/$username');

  Future<void> resetUserPassword(String username, String newPassword) async {
    await _postJson('/api/auth/users/$username/reset-password', {'new_password': newPassword});
  }

  // ── System / health ──────────────────────────────────────────────────
  Future<Map<String, dynamic>> getHealthDetailed() async =>
      (await _get('/health/detailed')) as Map<String, dynamic>;

  // ── AI model ─────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getModelStatus() async =>
      (await _get('/api/model/status')) as Map<String, dynamic>;

  Future<Map<String, dynamic>> getModelRegistry() async =>
      (await _get('/api/model/registry')) as Map<String, dynamic>;

  // ── Detection ─────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> detectReading(Map<String, dynamic> reading) async =>
      (await _postJson('/api/detect', reading)) as Map<String, dynamic>;

  // ── Blockchain ───────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getBlockchainStatus() async =>
      (await _get('/api/blockchain/status')) as Map<String, dynamic>;

  Future<Map<String, dynamic>> getOnchainStatus() async =>
      (await _get('/api/blockchain/onchain/status')) as Map<String, dynamic>;

  Future<Map<String, dynamic>> triggerOnchainAnchor() async =>
      (await _postJson('/api/blockchain/onchain/anchor', {})) as Map<String, dynamic>;

  // ── Alerts / grid ────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getAlerts() async =>
      (await _get('/api/alerts')) as Map<String, dynamic>;

  Future<Map<String, dynamic>> getGridAll() async =>
      (await _get('/api/grid/all')) as Map<String, dynamic>;
}

class ApiException implements Exception {
  final int statusCode;
  final String body;
  ApiException(this.statusCode, this.body);

  String get friendlyMessage {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map && decoded['detail'] != null) return decoded['detail'].toString();
      if (decoded is Map && decoded['error'] != null) return decoded['error'].toString();
    } catch (_) {/* body wasn't JSON */}
    return 'Request failed ($statusCode)';
  }

  @override
  String toString() => 'ApiException($statusCode): $body';
}

class SocketException implements Exception {
  final String message;
  SocketException(this.message);
  @override
  String toString() => 'SocketException: $message';
}

class TimeoutException implements Exception {
  final String message;
  TimeoutException(this.message);
  @override
  String toString() => 'TimeoutException: $message';
}
