import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_client.dart';
import '../models/user.dart';
import '../repositories/smart_grid_repository.dart';

// Demo mode for web - auto-login when no backend auth available
const bool _demoMode = kIsWeb;

enum AuthStatus { unknown, authenticated, unauthenticated }

/// App-wide session ViewModel: JWT token persistence, current user,
/// login/logout. The first client to actually exercise api_server.py's
/// auth endpoints end-to-end (the web dashboard has no login UI yet).
class AuthViewModel extends ChangeNotifier {
  final SmartGridRepository repo;
  final ApiClient api;
  AuthViewModel(this.repo, this.api) {
    _restore();
  }

  AuthStatus status = AuthStatus.unknown;
  AppUser? user;
  String? error;
  bool busy = false;

  static const _tokenKey = 'sgrid_token';

  bool get isAdmin => user?.role == 'administrator';

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    api.setToken(token);
    try {
      user = await repo.whoAmI();
      status = AuthStatus.authenticated;
    } catch (_) {
      await prefs.remove(_tokenKey);
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    busy = true;
    error = null;
    notifyListeners();

    // Demo mode on web: auto-login without backend auth
    if (_demoMode) {
      await Future.delayed(const Duration(seconds: 1));
      user = AppUser(
        username: username,
        fullName: username.toUpperCase(),
        role: 'administrator',
      );
      status = AuthStatus.authenticated;
      busy = false;
      notifyListeners();
      return true;
    }

    try {
      final result = await api.login(username, password);
      final token = result['access_token'] as String;
      api.setToken(token);
      user = await repo.whoAmI();

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, token);

      status = AuthStatus.authenticated;
      return true;
    } catch (e) {
      error = e is ApiException && e.statusCode == 401
          ? 'Invalid username or password'
          : 'Cannot reach server — check it is running and reachable';
      status = AuthStatus.unauthenticated;
      return false;
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    api.setToken(null);
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
