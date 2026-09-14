import 'package:flutter/material.dart';

/// Design tokens mirrored from the web dashboard (frontend/src/styles/tokens.css)
/// so the mobile app reads as the same platform, not a different product.
class AppColors {
  static const background = Color(0xFF0B1220);
  static const card = Color(0xFF111827);
  static const cardHover = Color(0xFF1A2333);
  static const border = Color(0xFF1E293B);

  static const textPrimary = Color(0xFFF1F5F9);
  static const textSecondary = Color(0xFF94A3B8);
  static const textMuted = Color(0xFF64748B);

  static const primary = Color(0xFF3B82F6);
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFF59E0B);
  static const critical = Color(0xFFEF4444);
  static const info = Color(0xFF06B6D4);

  static Color dim(Color c) => c.withValues(alpha: 0.14);
}

final ThemeData appTheme = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  scaffoldBackgroundColor: AppColors.background,
  colorScheme: const ColorScheme.dark(
    primary: AppColors.primary,
    secondary: AppColors.info,
    surface: AppColors.card,
    error: AppColors.critical,
  ),
  fontFamily: 'Roboto',
  appBarTheme: const AppBarTheme(
    backgroundColor: AppColors.background,
    foregroundColor: AppColors.textPrimary,
    elevation: 0,
    centerTitle: false,
  ),
  cardTheme: CardThemeData(
    color: AppColors.card,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(12),
      side: const BorderSide(color: AppColors.border),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: AppColors.card,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: AppColors.border),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: AppColors.border),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
    ),
    labelStyle: const TextStyle(color: AppColors.textSecondary),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
    ),
  ),
  textTheme: const TextTheme(
    headlineSmall: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700),
    titleMedium: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
    bodyMedium: TextStyle(color: AppColors.textSecondary),
    bodySmall: TextStyle(color: AppColors.textMuted),
  ),
  dividerColor: AppColors.border,
);

/// Status tone -> color, mirrors Badge.jsx's tone system.
Color toneColor(String tone) {
  switch (tone) {
    case 'success':
      return AppColors.success;
    case 'warning':
      return AppColors.warning;
    case 'critical':
      return AppColors.critical;
    case 'info':
      return AppColors.info;
    default:
      return AppColors.primary;
  }
}
