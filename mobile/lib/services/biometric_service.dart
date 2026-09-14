import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

class BiometricService {
  static final BiometricService _instance = BiometricService._internal();
  final LocalAuthentication _localAuth = LocalAuthentication();
  bool _isBiometricAvailable = false;
  List<BiometricType> _availableBiometrics = [];

  factory BiometricService() => _instance;

  BiometricService._internal();

  Future<void> initialize() async {
    try {
      _isBiometricAvailable = await _localAuth.canCheckBiometrics;
      if (_isBiometricAvailable) {
        _availableBiometrics = await _localAuth.getAvailableBiometrics();
        debugPrint('✓ Biometric available: $_availableBiometrics');
      }
    } catch (e) {
      debugPrint('Biometric check error: $e');
    }
  }

  bool get isBiometricAvailable => _isBiometricAvailable;
  bool get hasFaceID => _availableBiometrics.contains(BiometricType.face);
  bool get hasFingerprint => _availableBiometrics.contains(BiometricType.fingerprint);
  List<BiometricType> get availableBiometrics => _availableBiometrics;

  Future<bool> authenticate({
    required String reason,
  }) async {
    if (!_isBiometricAvailable) return false;

    try {
      return await _localAuth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true,
        ),
      );
    } catch (e) {
      debugPrint('Biometric auth error: $e');
      return false;
    }
  }

  Future<void> enableBiometric() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('biometric_enabled', true);
    debugPrint('✓ Biometric enabled');
  }

  Future<void> disableBiometric() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('biometric_enabled', false);
    debugPrint('✓ Biometric disabled');
  }

  Future<bool> isBiometricEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool('biometric_enabled') ?? false;
  }
}
