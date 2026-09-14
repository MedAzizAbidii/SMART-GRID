import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart';

class AppVersionService {
  static final AppVersionService _instance = AppVersionService._internal();
  static const String _version = '1.0.0';
  static const String _buildNumber = '1';

  factory AppVersionService() => _instance;

  AppVersionService._internal();

  Future<void> initialize() async {
    debugPrint('✓ App Version: $_version (Build $_buildNumber)');
  }

  String get currentVersion => _version;
  String get buildNumber => _buildNumber;

  Future<bool> checkForUpdates(String latestVersion) async {
    final current = _parseVersion(_version);
    final latest = _parseVersion(latestVersion);

    for (int i = 0; i < current.length && i < latest.length; i++) {
      if (latest[i] > current[i]) return true;
      if (latest[i] < current[i]) return false;
    }
    return latest.length > current.length;
  }

  Future<void> markUpdateAsViewed(String version) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('last_viewed_version', version);
  }

  List<int> _parseVersion(String version) {
    return version.split('.').map((e) => int.tryParse(e) ?? 0).toList();
  }
}
